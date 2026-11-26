"""Extract the designers' pen strokes from the SMC Malayalam fonts; build the font-based set."""

# Two modes:
#
#   extract  reads the per-glyph SVG sources of Chilanka and Manjari (SMC, SIL Open Font License)
#            and writes every cluster's pen strokes, per font, in Jayasree's coordinates, to
#            js/src/font-strokes.ml.json.
#   build    reads that file plus the choices made in tools/font-stroke-chooser.html (which font's
#            strokes to use for each cluster) and writes js/src/stroke-data.font.json: the
#            font-based stroke set, in the format of stroke-data.json, which a writer loads with
#            loadStrokes().
#
# The SVGs hold one pen path per stroke (a stroked path, `fill:none`). Manjari's files also hold
# the filled outline paths, which are skipped, and several weights of the same glyph drawn side
# by side, of which the one that fits Manjari Regular's outline is kept. Every font's strokes are
# then centred on the Manjari outline of the same cluster, so the fonts are comparable and fit
# Jayasree's layout. Units: the SVG canvas is the font's 2048-unit em, the same as Jayasree's.

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

import numpy as np  # noqa: E402
from svgpathtools import CubicBezier, Line, QuadraticBezier, parse_path  # noqa: E402
from svgpathtools import Path as SvgPath  # noqa: E402

from jayasree import centering, stroke_compose  # noqa: E402
from jayasree.cleanup import ink  # noqa: E402

GLYPH_DATA = ROOT / "js" / "src" / "glyph-data.json"
CANDIDATES = ROOT / "js" / "src" / "font-strokes.ml.json"
CHOICES = ROOT / "tools" / "font-stroke-choices.ml.json"
OUTPUT = ROOT / "js" / "src" / "stroke-data.font.json"

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"
FONTS = ("Chilanka", "Manjari")
#: Strokes closer than this (font units) belong to one copy of a glyph (copies sit side by side).
COPY_GAP_FU = 40.0
#: Groups whose width and height differ by less than this fraction are copies of one letter.
SAME_SIZE = 0.2
#: A Manjari copy that beat the runner-up by less than this (font units) is a near-tie, reported.
NEAR_TIE_FU = 3.0
#: Stroke width of the fonts' pen strokes (font units): an outline reaches half of it past a stroke.
INK_FU = 130.0
#: Most a Chilanka letter is stretched or squeezed sideways to fill its Manjari letter's width.
WIDTH_SCALE = (0.7, 1.4)
#: Nupuram draws on another unit size, so its strokes are scaled to the Manjari outline (limits).
BOX_SCALE = (0.4, 3.0)
#: How Nupuram's debug build styles a glyph's centre lines (its Makefile's ``VARIANT=debug`` SVGs).
MP_CENTRELINE = "stroke:rgb(80.000305%,80.000305%,80.000305%)"
NUPURAM = "Nupuram"
#: Strokes with at least this share of their length on the ink are well placed; others are searched.
REFINE_ABOVE = 0.9
#: How far (font units) and in what steps badly placed strokes are moved while looking for the ink.
REFINE_RANGE_FU = 700
REFINE_STEP_FU = 25
#: A new position is only taken if it puts this much more of the strokes on the ink.
REFINE_GAIN = 0.1
#: A legacy chillu (consonant + virama + ZWJ) -> its atomic codepoint, as the SVG files name them.
LEGACY_CHILLU = {
    "ക്‍": "ൿ",
    "ണ്‍": "ൺ",
    "ന്‍": "ൻ",
    "ര്‍": "ർ",
    "ല്‍": "ൽ",
    "ള്‍": "ൾ",
}
_NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _multiply(m: Matrix, n: Matrix) -> Matrix:
    """Return the matrix product m * n (n applied first), as SVG ``(a, b, c, d, e, f)``."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def parse_transform(text: str | None) -> Matrix:
    """Parse an SVG ``transform`` attribute (translate, scale and matrix) into one matrix.

    Parameters
    ----------
    text : str | None
        The attribute's value, or ``None`` if the element has none.

    Returns
    -------
    Matrix
        ``(a, b, c, d, e, f)``; the identity for no transform.
    """
    result = IDENTITY
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.findall(_NUM, args)]
        if name == "translate":
            m = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            m = (v[0], 0.0, 0.0, v[1] if len(v) > 1 else v[0], 0.0, 0.0)
        elif name == "matrix" and len(v) == 6:
            m = tuple(v)
        else:
            raise ValueError(f"unsupported transform: {name}")
        result = _multiply(result, m)
    return result


def _apply(m: Matrix, z: complex) -> complex:
    a, b, c, d, e, f = m
    return complex(a * z.real + c * z.imag + e, b * z.real + d * z.imag + f)


def path_d(d: str, m: Matrix) -> str:
    """Return the SVG path `d` with matrix `m` applied, as an absolute path with one decimal.

    Parameters
    ----------
    d : str
        An SVG path (lines and Beziers).
    m : Matrix
        The affine matrix to apply.

    Returns
    -------
    str
        The transformed path, ``M x y C ...``.
    """
    return _serialize(parse_path(d), m)


def _serialize(path: SvgPath, m: Matrix) -> str:
    """Return `path` with matrix `m` applied, as an absolute path with one decimal."""
    out: list[str] = []
    end: complex | None = None
    for seg in path:
        if isinstance(seg, Line):
            pts = [seg.end]
            cmd = "L"
        elif isinstance(seg, QuadraticBezier):
            pts = [seg.control, seg.end]
            cmd = "Q"
        elif isinstance(seg, CubicBezier):
            pts = [seg.control1, seg.control2, seg.end]
            cmd = "C"
        else:
            raise ValueError(f"unsupported segment: {type(seg).__name__}")
        if (
            end is None or abs(seg.start - end) > 1e-6
        ):  # the first segment, or a pen lift (a new subpath)
            p = _apply(m, seg.start)
            out.append(f"M {p.real:.1f} {p.imag:.1f}")
        end = seg.end
        out.append(
            cmd
            + " "
            + " ".join(f"{q.real:.1f} {q.imag:.1f}" for q in map(lambda z: _apply(m, z), pts))
        )
    return " ".join(out)


def reverse_d(d: str) -> str:
    """Return the path `d` drawn the other way: it starts where `d` ends, and ends where it starts.

    Parameters
    ----------
    d : str
        An SVG path (lines and Beziers).

    Returns
    -------
    str
        The reversed path, in the same absolute one-decimal form as :func:`path_d`.
    """
    path = parse_path(d)
    return _serialize(SvgPath(*[seg.reversed() for seg in reversed(path)]), IDENTITY)


def _is_pen_stroke(node: ET.Element) -> bool:
    """Return True for a path drawing a line: a visible stroke, and no fill or an open path."""
    # A straight pen stroke is sometimes saved with a fill as well (a line has no area, so it makes
    # no difference); a closed path with a stroke and a fill is an outline, not a pen stroke.
    props = {k: node.get(k, "") for k in ("fill", "stroke")}
    style = dict(kv.split(":", 1) for kv in node.get("style", "").split(";") if ":" in kv)
    props.update({k: style[k] for k in ("fill", "stroke") if k in style})
    if props["stroke"].strip() in ("", "none"):
        return False
    if props["fill"].strip() == "none":
        return True
    d = node.get("d", "").strip()
    return bool(d) and not d.endswith(("z", "Z"))


def svg_strokes(svg_path: Path) -> list[str]:
    """Return the pen strokes of one glyph SVG, in Jayasree's coordinates, in document order.

    Parameters
    ----------
    svg_path : Path
        A per-glyph SVG from a font's ``sources/svgs`` folder.

    Returns
    -------
    list[str]
        One path ``d`` per stroke; empty if the file has none.
    """
    root = ET.parse(svg_path).getroot()
    strokes: list[str] = []

    def walk(node: ET.Element, m: Matrix, baseline: float | None) -> None:
        for child in node:
            cm = _multiply(m, parse_transform(child.get("transform")))
            if child.tag == f"{SVG}g":
                is_layer = child.get(f"{INKSCAPE}groupmode") == "layer"
                # the layer's own translate(0, N) puts the baseline at y = N: take it out
                walk(child, cm, cm[5] if (is_layer and baseline is None) else baseline)
            elif child.tag == f"{SVG}path" and child.get("d") and _is_pen_stroke(child):
                strokes.append(
                    path_d(
                        child.get("d"), _multiply((1.0, 0.0, 0.0, 1.0, 0.0, -(baseline or 0.0)), cm)
                    )
                )

    walk(root, IDENTITY, None)
    return strokes


def _bounds(d: str) -> tuple[float, float, float, float]:
    """Return a path's ``(xmin, xmax, ymin, ymax)``."""
    return parse_path(d).bbox()


def _shift(d: str, dx: float, dy: float = 0.0) -> str:
    """Return the path `d` moved by ``(dx, dy)``."""
    return path_d(d, (1.0, 0.0, 0.0, 1.0, dx, dy))


def _ghost_centre(ghost: list[dict]) -> tuple[float, float]:
    """Return the centre of the cluster's outline (glyph offsets included), in font units."""
    boxes = [
        (b[0] + g["x"], b[1] + g["x"], b[2] + g["y"], b[3] + g["y"])
        for g in ghost
        for b in [parse_path(g["d"]).bbox()]
    ]
    return (min(b[0] for b in boxes) + max(b[1] for b in boxes)) / 2, (
        min(b[2] for b in boxes) + max(b[3] for b in boxes)
    ) / 2


def _sample(strokes: list[str]) -> np.ndarray:
    """Return points sampled along the strokes, ``(n, 2)``."""
    ts = np.linspace(0, 1, 60)
    return np.array([(z.real, z.imag) for d in strokes for z in map(parse_path(d).point, ts)])


def _on_ink(pts: np.ndarray, field: centering.DistField, dx: float, dy: float) -> float:
    """Return the share of `pts`, moved by ``(dx, dy)``, that lie on the ink."""
    rows, cols = centering.fu_to_px(field, pts[:, 0] + dx, pts[:, 1] + dy)
    last = centering.RASTER_SIZE - 1
    depth = field.dist[np.clip(rows.astype(int), 0, last), np.clip(cols.astype(int), 0, last)]
    return float(np.mean(depth > 0))


def refine_placement(strokes: list[str], field: centering.DistField) -> list[str]:
    """Move strokes that sit off the ink onto it, for a font file that only holds part of a cluster.

    Parameters
    ----------
    strokes : list[str]
        Strokes already centred on the cluster's outline.
    field : centering.DistField
        The cluster's distance field.

    Returns
    -------
    list[str]
        The strokes unchanged if they already sit on the ink; otherwise shifted to where most of
        them do. A cluster stacked from two letters, where the file draws only one, needs this:
        centring that one letter on the whole cluster leaves it between the two.
    """
    pts = _sample(strokes)
    inside = _on_ink(pts, field, 0.0, 0.0)
    if inside >= REFINE_ABOVE:
        return strokes
    offsets = range(-REFINE_RANGE_FU, REFINE_RANGE_FU + 1, REFINE_STEP_FU)
    best = max(
        ((dx, dy) for dx in offsets for dy in offsets),
        key=lambda o: (_on_ink(pts, field, *o), -abs(o[0]) - abs(o[1])),
    )
    if _on_ink(pts, field, *best) - inside < REFINE_GAIN:
        return strokes
    return [_shift(d, best[0], best[1]) for d in strokes]


def reference_glyphs(glyphs: list[dict], mark: dict | None) -> list[dict]:
    """Return the glyphs a cluster's strokes are placed on: a mark's own shape, no placeholder.

    Parameters
    ----------
    glyphs : list[dict]
        The cluster's glyph entries from ``glyph-data.json``.
    mark : dict | None
        The cluster's entry in the ``marks`` table, if it is a mark.

    Returns
    -------
    list[dict]
        For a mark shaped as placeholder circle + content, only the content; otherwise `glyphs`.
    """
    if len(glyphs) != 2 or not mark:
        return glyphs
    return [glyphs[0]] if mark["prefix"] else [glyphs[-1]]


def fit_to_ghost(strokes: list[str], ghost: list[dict]) -> list[str]:
    """Move a glyph's strokes so their bounding box is centred on the cluster's Manjari outline.

    Parameters
    ----------
    strokes : list[str]
        One copy of a glyph's pen strokes.
    ghost : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data.json``.

    Returns
    -------
    list[str]
        The strokes, shifted. Fonts draw a letter at their own width and height, so centring on the
        Manjari outline is what makes them comparable, and usable with Jayasree's layout.
    """
    boxes = [_bounds(d) for d in strokes]
    cx = (min(b[0] for b in boxes) + max(b[1] for b in boxes)) / 2
    cy = (min(b[2] for b in boxes) + max(b[3] for b in boxes)) / 2
    gx, gy = _ghost_centre(ghost)
    return [_shift(d, gx - cx, gy - cy) for d in strokes]


def split_copies(strokes: list[str]) -> list[list[str]]:
    """Group a glyph's strokes into the copies drawn apart in the file (Manjari has several).

    Parameters
    ----------
    strokes : list[str]
        Every pen stroke in the file, in document order.

    Returns
    -------
    list[list[str]]
        One list of strokes per group, in document order. Strokes whose bounding boxes lie within
        ``COPY_GAP_FU`` of each other, in either direction, are one group; copies may sit in a grid.
    """
    boxes = [_bounds(d) for d in strokes]
    parent = list(range(len(strokes)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            if a[0] <= b[1] + COPY_GAP_FU and b[0] <= a[1] + COPY_GAP_FU:
                if a[2] <= b[3] + COPY_GAP_FU and b[2] <= a[3] + COPY_GAP_FU:
                    parent[find(i)] = find(j)
    groups: dict[int, list[str]] = {}
    for i, d in enumerate(strokes):
        groups.setdefault(find(i), []).append(d)
    return sorted(groups.values(), key=lambda g: strokes.index(g[0]))


def are_weights(copies: list[list[str]]) -> bool:
    """Return True if the groups are one letter repeated (as weights), not different parts of it.

    Parameters
    ----------
    copies : list[list[str]]
        The groups from :func:`split_copies`.

    Returns
    -------
    bool
        True if every group has the same number of strokes and about the same size as the first.
        Anything else is different parts or characters, all of which must be kept.
    """
    if len({len(c) for c in copies}) > 1:
        return False
    sizes = []
    for copy in copies:
        boxes = [_bounds(d) for d in copy]
        sizes.append(
            (
                max(b[1] for b in boxes) - min(b[0] for b in boxes),
                max(b[3] for b in boxes) - min(b[2] for b in boxes),
            )
        )
    w0, h0 = sizes[0]
    return all(
        abs(w - w0) <= SAME_SIZE * max(w0, 1) and abs(h - h0) <= SAME_SIZE * max(h0, 1)
        for w, h in sizes
    )


def _ink_score(strokes: list[str], field: centering.DistField) -> float:
    """Return the mean ink depth (font units) under a copy's strokes (0 or less: off the glyph)."""
    scale = field.w / centering.RASTER_SIZE
    depths = []
    for d in strokes:
        path = parse_path(d)
        for t in np.linspace(0, 1, 60):
            z = path.point(t)
            r, c = centering.fu_to_px(field, z.real, z.imag)
            last = centering.RASTER_SIZE - 1
            depths.append(
                float(field.dist[int(np.clip(r, 0, last)), int(np.clip(c, 0, last))]) * scale
            )
    return float(np.mean(depths))


def pick_copy(copies: list[list[str]], ghost: list[dict]) -> tuple[list[str], float]:
    """Return the copy that is the glyph as the Manjari font draws it, moved onto the ghost outline.

    Parameters
    ----------
    copies : list[list[str]]
        The copies from :func:`split_copies`.
    ghost : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data.json``.

    Returns
    -------
    tuple[list[str], float]
        The best-matching copy's strokes, centred on the ghost, and how much better its score is
        than the runner-up's (font units; 0 if there is one copy). A small margin is a near-tie.
    """
    field = ink.make_field_winding(ghost)
    scored = sorted(
        ((_ink_score(moved, field), moved) for moved in (fit_to_ghost(c, ghost) for c in copies)),
        key=lambda item: -item[0],
    )
    margin = scored[0][0] - scored[1][0] if len(scored) > 1 else 0.0
    return scored[0][1], margin


def mp_strokes(svg_path: Path) -> list[str]:
    """Return the designer's centre lines from a Nupuram glyph SVG built with its ``debug`` variant.

    Parameters
    ----------
    svg_path : Path
        An SVG from running Nupuram's ``make VARIANT=debug`` (MetaPost) on one glyph.

    Returns
    -------
    list[str]
        One path ``d`` per centre line, in the order the designer defined them.
    """
    text = svg_path.read_text(encoding="utf-8")
    out = []
    for d, style in re.findall(r'<path d="([^"]*)" style="([^"]*)"', text):
        flat = style.replace(" ", "")
        if MP_CENTRELINE in flat and "fill:none" in flat and not d.strip().endswith(("z", "Z")):
            out.append(path_d(d, IDENTITY))
    return out


def _ghost_box(ghost: list[dict]) -> tuple[float, float, float, float]:
    """Return the outline's ``(x0, x1, y0, y1)``, glyph offsets included."""
    boxes = [
        (b[0] + g["x"], b[1] + g["x"], b[2] + g["y"], b[3] + g["y"])
        for g in ghost
        for b in [parse_path(g["d"]).bbox()]
    ]
    return (
        min(b[0] for b in boxes),
        max(b[1] for b in boxes),
        min(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def fit_box(strokes: list[str], ghost: list[dict]) -> list[str]:
    """Scale and move strokes drawn on another unit size onto the cluster's Manjari outline.

    Parameters
    ----------
    strokes : list[str]
        One cluster's strokes, in their own font's units.
    ghost : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data.json``.

    Returns
    -------
    list[str]
        The strokes scaled, each direction on its own, so their box fills the outline's box less
        half a stroke width on every side, within ``BOX_SCALE``.
    """
    boxes = [_bounds(d) for d in strokes]
    x0, x1 = min(b[0] for b in boxes), max(b[1] for b in boxes)
    y0, y1 = min(b[2] for b in boxes), max(b[3] for b in boxes)
    gx0, gx1, gy0, gy1 = _ghost_box(ghost)
    left, right, top, bottom = (
        gx0 + INK_FU / 2,
        gx1 - INK_FU / 2,
        gy0 + INK_FU / 2,
        gy1 - INK_FU / 2,
    )

    def scale(have: float, want: float) -> float:
        return min(max(want / have, BOX_SCALE[0]), BOX_SCALE[1]) if have > 1 and want > 1 else 1.0

    sx, sy = scale(x1 - x0, right - left), scale(y1 - y0, bottom - top)
    tx = (left + right) / 2 - sx * (x0 + x1) / 2
    ty = (top + bottom) / 2 - sy * (y0 + y1) / 2
    return [path_d(d, (sx, 0.0, 0.0, sy, tx, ty)) for d in strokes]


def cluster_name(stem: str) -> str:
    """Return the Jayasree cluster an SVG file name stands for.

    Parameters
    ----------
    stem : str
        The file name without its extension.

    Returns
    -------
    str
        The name in NFC, with a legacy chillu (consonant + virama + ZWJ) mapped to its atom.
    """
    name = unicodedata.normalize("NFC", stem)
    return LEGACY_CHILLU.get(name, name)


def extract(
    sources: dict[str, Path], glyph_data: dict, near_ties: list[str] | None = None
) -> dict[str, dict[str, list[str]]]:
    """Read every font's glyph SVGs and return ``{cluster: {font: [stroke d, ...]}}``.

    Parameters
    ----------
    sources : dict[str, Path]
        Font name -> the font repository's ``sources/svgs`` folder.
    glyph_data : dict
        Jayasree's ``glyph-data.json``: Manjari's outline per cluster, to pick and place its copy.
    near_ties : list[str] | None
        If given, the clusters whose Manjari copy was picked by a margin under ``NEAR_TIE_FU`` are
        appended to it, for a person to check.

    Returns
    -------
    dict[str, dict[str, list[str]]]
        Only Malayalam clusters that have at least one pen stroke in some font.
    """
    out: dict[str, dict[str, list[str]]] = {}
    near_ties = [] if near_ties is None else near_ties
    for font, folder in sources.items():
        for svg in sorted(folder.glob("*.svg")):
            name = cluster_name(svg.stem)
            if not any("ഀ" <= c <= "ൿ" for c in name):
                continue
            strokes = mp_strokes(svg) if font == NUPURAM else svg_strokes(svg)
            if strokes:
                mark = glyph_data.get("marks", {}).get(name)
                info = glyph_data["clusters"].get(name)
                if not info and mark:
                    info = {"glyphs": mark["prefix"] + mark["suffix"]}  # a mark: its own shape
                if not info:
                    continue  # nothing to place it on: not a cluster Jayasree draws
                ghost = reference_glyphs(info["glyphs"], mark)
                if font == NUPURAM:
                    out.setdefault(name, {})[font] = refine_placement(
                        fit_box(strokes, ghost), ink.make_field_winding(ghost)
                    )
                    continue
                copies = split_copies(strokes) if font == "Manjari" else [strokes]
                field = ink.make_field_winding(ghost)
                if len(copies) > 1 and are_weights(copies):
                    strokes, margin = pick_copy(copies, ghost)
                    strokes = refine_placement(strokes, field)
                    if margin < NEAR_TIE_FU:
                        near_ties.append(name)
                else:
                    if len(copies) > 1:
                        # The copies cannot be told apart, so show everything: all the strokes as
                        # the font's option, and each group on its own, for a person to choose.
                        for i, group in enumerate(copies, 1):
                            placed = refine_placement(fit_to_ghost(group, ghost), field)
                            out.setdefault(name, {})[f"{font} (part {i})"] = placed
                    strokes = refine_placement(
                        fit_to_ghost([d for c in copies for d in c], ghost), field
                    )
            if strokes:
                out.setdefault(name, {})[font] = strokes
    return out


def fit_width(strokes: list[str], ghost: list[dict]) -> list[str]:
    """Stretch strokes sideways so their ink spans the same width as the cluster's Manjari outline.

    Parameters
    ----------
    strokes : list[str]
        One cluster's chosen strokes.
    ghost : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data.json``.

    Returns
    -------
    list[str]
        The strokes with their left and right edges where Manjari's letter has its own (an outline
        reaches half a stroke width past the strokes). Letters from another font have other widths
        and side margins, so without this the gaps between letters differ from one to the next.
    """
    boxes = [_bounds(d) for d in strokes]
    x0, x1 = min(b[0] for b in boxes), max(b[1] for b in boxes)
    outline = [(parse_path(g["d"]).bbox(), g["x"]) for g in ghost]
    left = min(b[0] + dx for b, dx in outline) + INK_FU / 2
    right = max(b[1] + dx for b, dx in outline) - INK_FU / 2
    if x1 - x0 < 1 or right - left < 1:
        return strokes
    scale = min(max((right - left) / (x1 - x0), WIDTH_SCALE[0]), WIDTH_SCALE[1])
    shift = (left + right) / 2 - scale * (x0 + x1) / 2
    return [path_d(d, (scale, 0.0, 0.0, 1.0, shift, 0.0)) for d in strokes]


def build(
    candidates: dict, choices: dict[str, list[str]], glyph_data: dict | None = None
) -> dict[str, dict]:
    """Return the font-based stroke set: for each cluster, the strokes chosen for it, in order.

    Parameters
    ----------
    candidates : dict
        The output of :func:`extract`.
    choices : dict[str, list[str]]
        Cluster -> the chosen strokes, each ``"<option>:<number from 1>"`` (``"Manjari:2"``,
        ``"Manjari (part 3):1"``), as the chooser exports them. A trailing ``~`` means the stroke
        is drawn the other way round (``"Manjari:2~"``).
    glyph_data : dict | None
        Jayasree's ``glyph-data.json``. If given, a letter drawn only from Chilanka is stretched
        sideways to the width of its Manjari outline (see :func:`fit_width`), so spacing is the
        same whichever font a letter came from. Marks are left alone: their placement is relative.

    Returns
    -------
    dict[str, dict]
        ``{cluster: {"strokes": [{"d": ...}, ...]}}``, the shape of ``stroke-data.json``.

    Raises
    ------
    ValueError
        If a choice names a cluster, option or stroke that ``candidates`` does not have, so a
        stale choices file fails loudly instead of building a letter with strokes missing.
    """
    out: dict[str, dict] = {}
    for cluster, ids in choices.items():
        strokes = []
        for stroke_id in ids:
            reverse = stroke_id.endswith("~")
            option, _, number = stroke_id.removesuffix("~").rpartition(":")
            try:
                d = candidates[cluster][option][int(number) - 1]
            except (KeyError, IndexError, ValueError) as exc:
                raise ValueError(f"unknown stroke {stroke_id!r} for {cluster!r}") from exc
            strokes.append({"d": reverse_d(d) if reverse else d})
        if not strokes:
            continue
        only_chilanka = not any(i.startswith("Manjari") for i in ids)
        info = (glyph_data or {}).get("clusters", {}).get(cluster)
        if only_chilanka and info and cluster not in glyph_data.get("marks", {}):
            fitted = fit_width([s["d"] for s in strokes], info["glyphs"])
            strokes = [{"d": d} for d in fitted]
        out[cluster] = {"strokes": strokes}
    return out


def bake(glyph_data: dict, atoms: dict) -> tuple[dict, list[str]]:
    """Compose every cluster that can be built from the chosen strokes, as handwriting is.

    Parameters
    ----------
    glyph_data : dict
        Jayasree's ``glyph-data.json``.
    atoms : dict
        The chosen font strokes, ``{cluster: {"strokes": [...]}}``, as :func:`build` returns them.

    Returns
    -------
    tuple[dict, list[str]]
        The atoms plus every composed cluster (the same step ``process_strokes.py --expand`` runs
        on the recorded handwriting), and the clusters this step could not compose. The engine
        composes some of those too, as it does for handwriting, so this is a superset of the
        clusters that really cannot be written. A base + sign that the font draws as one glyph is
        written base, gap, sign, gap, with the ``advance`` it needs (``stitch_ligature``), not
        left for the engine, which would put the sign on the next letter.
    """
    import stitch_font_strokes  # it imports this module, so only when needed

    full, _, _ = stroke_compose.compose_all(glyph_data, atoms)
    for cluster in stitch_font_strokes.ligature_clusters(glyph_data, atoms, full):
        strokes, advance = stitch_font_strokes.stitch_ligature(cluster, glyph_data, atoms)
        full[cluster] = {"strokes": [{"d": d} for d in strokes], "advance": advance}
    missing = sorted(c for c in glyph_data["clusters"] if not full.get(c, {}).get("strokes"))
    return full, missing


def main() -> None:
    """Run the ``extract`` or ``build`` mode from the command line."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    ex = sub.add_parser("extract", help="read the fonts' SVG sources")
    for font in FONTS:
        ex.add_argument(
            f"--{font.lower()}", type=Path, required=True, help=f"{font} repository folder"
        )
    ex.add_argument(
        "--nupuram",
        type=Path,
        help="Nupuram repository folder, after `make VARIANT=debug` in its sources/ (optional)",
    )
    ex.add_argument("--out", type=Path, default=CANDIDATES)
    bd = sub.add_parser("build", help="build the font-based stroke set from the choices")
    bd.add_argument("--candidates", type=Path, default=CANDIDATES)
    bd.add_argument("--choices", type=Path, default=CHOICES)
    bd.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args()
    if args.mode == "extract":
        glyphs = json.loads(GLYPH_DATA.read_text("utf-8"))
        ties: list[str] = []
        sources = {f: getattr(args, f.lower()) / "sources" / "svgs" for f in FONTS}
        if args.nupuram:
            sources[NUPURAM] = args.nupuram / "sources" / "svgs" / "debug"
        data = extract(sources, glyphs, ties)
        args.out.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        every = sum(1 for v in data.values() if len(v) >= len(sources))
        print(f"{len(data)} clusters ({every} in every font) -> {args.out}")
        if ties:
            print(f"{len(ties)} Manjari copies were picked by a near-tie; check: {' '.join(ties)}")
    else:
        glyphs = json.loads(GLYPH_DATA.read_text("utf-8"))
        atoms = build(
            json.loads(args.candidates.read_text("utf-8")),
            json.loads(args.choices.read_text("utf-8")),
            glyphs,
        )
        data, missing = bake(glyphs, atoms)
        args.out.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        print(f"{len(atoms)} chosen letters + {len(data) - len(atoms)} composed -> {args.out}")
        print(
            f"{len(data)} of {len(glyphs['clusters'])} clusters baked; the engine composes more"
            " while drawing (tools/coverage_report.js --stroke-data <this file> counts them)"
        )
        needed = sorted({ch for c in missing for ch in c if ch not in atoms})
        print(f"characters with no chosen strokes that they need: {' '.join(needed)}")


if __name__ == "__main__":
    main()
