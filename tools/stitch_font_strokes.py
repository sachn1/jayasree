"""Stitch strokes for clusters the fonts do not cover from the letters already chosen for them."""

# A conjunct such as ത്ന is two letters drawn together. Where the fonts have no strokes for it but
# the owner has chosen strokes for each of its letters, this script finds where each letter sits
# inside the conjunct's outline (a scale and a position that put the letter's ink on the
# conjunct's ink, cover what the earlier letters did not and do not pile onto them), and moves
# that letter's chosen strokes by the same amount. The result is added to the cluster's candidates
# as a "Stitched" option, so that tools/font-stroke-chooser.html shows it for approval.
#
# A cluster is only stitched if its letters cover at least MIN_COVER of its ink; a piece no chosen
# letter explains (a vowel sign's own shape, say) is left out and reported, never guessed.
#
# Usage:  python tools/stitch_font_strokes.py [--targets FILE] [--candidates FILE] [--choices FILE]
# (extract rewrites the candidates file: run this after it, and again after changing the choices.)

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import build_font_strokes as bfs  # noqa: E402

from jayasree import centering  # noqa: E402
from jayasree.cleanup import ink  # noqa: E402

STITCHED = "Stitched"
#: Independent vowels drawn as one letter plus a sign, which the text itself does not spell out.
COMPOSED = {
    "\u0d08": ["\u0d07", "\u0d57"],  # ഈ = ഇ + ൗ
    "\u0d0a": ["\u0d09", "\u0d57"],  # ഊ = ഉ + ൗ
    "\u0d10": ["\u0d0e", "\u0d46"],  # ഐ = എ + െ
    "\u0d13": ["\u0d12", "\u0d3e"],  # ഓ = ഒ + ാ
    "\u0d14": ["\u0d12", "\u0d57"],  # ഔ = ഒ + ൗ
    "\u0d48": ["\u0d46", "\u0d46"],  # ൈ = െ twice
}
VIRAMA = "്"
JOINERS = "‌‍"
#: A cluster is only stitched if its letters cover at least this share of its ink.
MIN_COVER = 0.85
#: How much of a letter's ink must lie on the cluster's ink for it to belong in it.
MIN_INSIDE = 0.8
#: Clusters whose parts are drawn closer together than the font sets them: the sideways gap, in font
#: units, to leave between a part and the parts before it.
PART_GAPS = {"\u0d37\u0d4d\u0d30": 100}  # ഷ്ര
#: A letter may overlap the ones already placed by up to this share of its ink.
MAX_OVERLAP = 0.15
#: The space left after a letter and its sign, before the next letter (font units).
ATOM_GAP = 150.0
#: How far the sign is moved at a time while it closes in on its base (font units).
SLIDE = 10.0
#: The least distance between a base's strokes and its sign's: small, but clear of the ink.
SIGN_CLEARANCE = 75.0
#: The signs that sit under or beside a letter and are written with room around them.
SIGNS = "\u0d41\u0d42\u0d43"  # ു ൂ ൃ
#: Scales tried for each letter, coarse then fine (the letter drawn smaller inside a conjunct).
COARSE_SCALES = np.arange(0.4, 1.21, 0.1)
FINE_SCALE_STEP = 0.025
#: Position search step, coarse then fine (font units).
COARSE_STEP, FINE_STEP = 60.0, 15.0
LETTER_POINTS, CLUSTER_POINTS = 500, 1200
CHUNK = 400


def _ink_points(field: centering.DistField, limit: int) -> np.ndarray:
    """Return up to `limit` font-unit points spread over the ink of `field`, ``(n, 2)``."""
    rows, cols = np.nonzero(field.dist > 0)
    step = max(1, len(rows) // limit)
    rows, cols = rows[::step], cols[::step]
    x = field.x_min + (cols + 0.5) / centering.RASTER_SIZE * field.w
    y = field.y_max - (rows + 0.5) / centering.RASTER_SIZE * field.h
    return np.column_stack([x, y])


def _on_ink(field: centering.DistField, pts: np.ndarray) -> np.ndarray:
    """Return, for points ``(..., 2)`` in font units, whether each lies on the ink of `field`."""
    rows, cols = centering.fu_to_px(field, pts[..., 0], pts[..., 1])
    size = centering.RASTER_SIZE
    within = (rows >= 0) & (rows < size) & (cols >= 0) & (cols < size)
    rows = np.clip(rows.astype(int), 0, size - 1)
    cols = np.clip(cols.astype(int), 0, size - 1)
    return within & (field.dist[rows, cols] > 0)


@dataclass
class Placement:
    """Where a letter sits in a cluster: ``p -> scale * p + (dx, dy)``, and what it covers."""

    scale: float
    dx: float
    dy: float
    inside: float  # the share of the letter's ink that lies on the cluster's
    covers: np.ndarray  # which of the cluster's sample points the letter's ink covers


def _score(
    scale: float,
    offsets: np.ndarray,
    letter: tuple[centering.DistField, np.ndarray],
    cluster: tuple[centering.DistField, np.ndarray],
    covered: np.ndarray,
    placed: list[tuple[centering.DistField, float, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Score each shift in `offsets` for one scale: ``(score, inside, covers)`` per shift."""
    letter_field, letter_pts = letter
    cluster_field, cluster_pts = cluster
    inside = np.empty(len(offsets))
    overlap = np.zeros(len(offsets))
    covers = np.empty((len(offsets), len(cluster_pts)), dtype=bool)
    for i in range(0, len(offsets), CHUNK):
        off = offsets[i : i + CHUNK, None, :]
        moved = scale * letter_pts[None] + off
        inside[i : i + CHUNK] = _on_ink(cluster_field, moved).mean(axis=1)
        for field, prev_scale, prev_off in placed:
            on_prev = _on_ink(field, (moved - prev_off) / prev_scale).mean(axis=1)
            overlap[i : i + CHUNK] = np.maximum(overlap[i : i + CHUNK], on_prev)
        covers[i : i + CHUNK] = _on_ink(letter_field, (cluster_pts[None] - off) / scale)
    gain = (covers & ~covered[None]).mean(axis=1)
    score = (
        gain - np.maximum(MIN_INSIDE - inside, 0) * 3.0 - np.maximum(overlap - MAX_OVERLAP, 0) * 3.0
    )
    return score, inside, covers


def _grid(centre_lo: np.ndarray, centre_hi: np.ndarray, step: float) -> np.ndarray:
    """Return grid points covering the box ``centre_lo .. centre_hi``, ``(k, 2)``."""
    xs = np.arange(centre_lo[0], centre_hi[0] + step, step)
    ys = np.arange(centre_lo[1], centre_hi[1] + step, step)
    return np.array([(x, y) for x in xs for y in ys])


def place_letter(
    letter: tuple[centering.DistField, np.ndarray],
    cluster: tuple[centering.DistField, np.ndarray],
    covered: np.ndarray,
    placed: list[tuple[centering.DistField, float, np.ndarray]] | None = None,
) -> Placement:
    """Find the scale and shift that best put a letter's ink onto the cluster's uncovered ink.

    Parameters
    ----------
    letter : tuple[centering.DistField, np.ndarray]
        The letter's distance field and sample points of its ink.
    cluster : tuple[centering.DistField, np.ndarray]
        The cluster's distance field and sample points of its ink.
    covered : np.ndarray
        Which of the cluster's sample points earlier letters already cover.
    placed : list[tuple[centering.DistField, float, np.ndarray]] | None
        The earlier letters as ``(field, scale, shift)``; a letter that sits on them is penalised.

    Returns
    -------
    Placement
        The best scale and shift found, by a coarse search and then a fine one around it.
    """
    placed = placed or []
    lcentre = (letter[1].min(axis=0) + letter[1].max(axis=0)) / 2
    lo, hi = cluster[1].min(axis=0), cluster[1].max(axis=0)
    best = (-1e9, 1.0, np.zeros(2), 0.0, np.zeros(len(cluster[1]), dtype=bool))
    for scale in COARSE_SCALES:
        offsets = _grid(lo, hi, COARSE_STEP) - scale * lcentre
        score, inside, covers = _score(scale, offsets, letter, cluster, covered, placed)
        k = int(np.argmax(score))
        if score[k] > best[0]:
            best = (score[k], scale, offsets[k], inside[k], covers[k])
    _, scale0, off0, _, _ = best
    for scale in np.arange(scale0 - 0.1, scale0 + 0.101, FINE_SCALE_STEP):
        offsets = off0 + _grid(np.array([-COARSE_STEP] * 2), np.array([COARSE_STEP] * 2), FINE_STEP)
        score, inside, covers = _score(scale, offsets, letter, cluster, covered, placed)
        k = int(np.argmax(score))
        if score[k] > best[0]:
            best = (score[k], scale, offsets[k], inside[k], covers[k])
    _, scale, off, inside, covers = best
    return Placement(float(scale), float(off[0]), float(off[1]), float(inside), covers)


def parts_of(cluster: str, atoms: dict) -> list[str] | None:
    """Split a cluster into the chosen letters and signs it is made of, left to right.

    Parameters
    ----------
    cluster : str
        The cluster, such as ``"ല്ല"``.
    atoms : dict
        The chosen strokes, ``{cluster: {"strokes": [...]}}``.

    Returns
    -------
    list[str] | None
        The parts (the longest chosen piece at each step; a virama on its own is not drawn), or
        ``None`` if some piece has no chosen strokes.
    """
    if cluster in COMPOSED and all(p in atoms for p in COMPOSED[cluster]):
        return list(COMPOSED[cluster])
    parts, i = [], 0
    while i < len(cluster):
        if cluster[i] == VIRAMA:  # a chosen tail such as ്ര or ്ല comes before a bare virama
            tail = next(
                (
                    cluster[i : i + n]
                    for n in range(len(cluster) - i, 1, -1)
                    if cluster[i : i + n] in atoms
                ),
                None,
            )
            if tail:
                parts.append(tail)
                i += len(tail)
                continue
        if cluster[i] in VIRAMA + JOINERS:
            i += 1
            continue
        for n in range(len(cluster) - i, 0, -1):
            piece = cluster[i : i + n]
            if piece in atoms and piece != cluster:
                parts.append(piece)
                i += n
                break
        else:
            return None
    return parts if len(parts) > 1 else None


def close_gaps(groups: list[list[str]], gap: float) -> list[str]:
    """Move each group of strokes sideways until it is `gap` away from the groups before it.

    Parameters
    ----------
    groups : list[list[str]]
        The stitched strokes of each part, in drawing order.
    gap : float
        The sideways distance to leave, in font units.

    Returns
    -------
    list[str]
        All the strokes, in order; a group that already sits closer than `gap` is left where it is.
    """
    out = list(groups[0])
    for group in groups[1:]:
        done = [parse_path(d).bbox() for d in out]
        mine = [parse_path(d).bbox() for d in group]
        lo, hi = min(b[0] for b in done), max(b[1] for b in done)
        mlo, mhi = min(b[0] for b in mine), max(b[1] for b in mine)
        shift = 0.0
        if mhi < lo and lo - mhi > gap:
            shift = lo - mhi - gap
        elif mlo > hi and mlo - hi > gap:
            shift = -(mlo - hi - gap)
        matrix = (1.0, 0.0, 0.0, 1.0, shift, 0.0)
        out += [bfs.path_d(d, matrix) for d in group]
    return out


def stitch_cluster(
    cluster: str, glyph_data: dict, atoms: dict, fields: dict, min_cover: float = MIN_COVER
) -> tuple[list[str] | None, float, str]:
    """Stitch one cluster's strokes from its chosen letters.

    Parameters
    ----------
    cluster : str
        The cluster to write.
    glyph_data : dict
        Jayasree's ``glyph-data.json``.
    atoms : dict
        The chosen strokes of every letter that has them.
    fields : dict
        A cache of distance fields by cluster, filled as needed.
    min_cover : float
        The least share of the cluster's ink its letters must cover.

    Returns
    -------
    tuple[list[str] | None, float, str]
        The stitched strokes (``None`` if it could not be done), the share of the cluster's ink the
        letters cover, and a short note saying what happened.
    """

    def field_of(name: str) -> centering.DistField:
        if name not in fields:
            mark = glyph_data.get("marks", {}).get(name)
            info = glyph_data["clusters"].get(name)
            glyphs = info["glyphs"] if info else mark["prefix"] + mark["suffix"]
            ghost = bfs.reference_glyphs(glyphs, mark)
            fields[name] = ink.make_field_winding(ghost)
        return fields[name]

    parts = parts_of(cluster, atoms)
    if parts is None:
        return None, 0.0, "a letter it is made of has no chosen strokes"
    cluster_field = field_of(cluster)
    cluster_pts = _ink_points(cluster_field, CLUSTER_POINTS)
    covered = np.zeros(len(cluster_pts), dtype=bool)
    groups: list[list[str]] = []
    placed: list[tuple[centering.DistField, float, np.ndarray]] = []
    for part in parts:
        letter_field = field_of(part)
        placement = place_letter(
            (letter_field, _ink_points(letter_field, LETTER_POINTS)),
            (cluster_field, cluster_pts),
            covered,
            placed,
        )
        placed.append((letter_field, placement.scale, np.array([placement.dx, placement.dy])))
        if placement.inside < MIN_INSIDE:
            return None, float(covered.mean()), f"{part} does not fit inside it"
        covered |= placement.covers
        matrix = (placement.scale, 0.0, 0.0, placement.scale, placement.dx, placement.dy)
        groups.append([bfs.path_d(s["d"], matrix) for s in atoms[part]["strokes"]])
    strokes = (
        close_gaps(groups, PART_GAPS[cluster])
        if cluster in PART_GAPS
        else [d for g in groups for d in g]
    )
    share = float(covered.mean())
    if share < min_cover:
        return None, share, f"its letters cover only {share:.0%} of it"
    return strokes, share, "stitched"


def sign_clusters(glyph_data: dict, atoms: dict, baked: dict) -> list[str]:
    """Return the clusters of a letter and a sign (ു ൂ ൃ) that are written with room between them.

    Parameters
    ----------
    glyph_data : dict
        Jayasree's ``glyph-data.json``.
    atoms : dict
        The chosen strokes, ``{cluster: {"strokes": [...]}}``.
    baked : dict
        Every cluster baked so far, atoms included, ``{cluster: {"strokes": [...]}}``.

    Returns
    -------
    list[str]
        The clusters, shortest first, that end in a sign, are not themselves chosen, and whose
        letter has strokes. Composing one the usual way sets the sign against the letter, or, where
        the font draws the two as one glyph, past the end of the cluster.
    """
    return sorted(
        (
            c
            for c in glyph_data["clusters"]
            if len(c) > 1
            and c not in atoms
            and c[-1] in SIGNS
            and c[-1] in atoms
            and baked.get(c[:-1], {}).get("strokes")
        ),
        key=len,
    )


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    """Return the least distance between any point of `a` and any point of `b`."""
    return float(np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2).min()))


def stitch_sign(
    cluster: str, glyph_data: dict, atoms: dict, baked: dict
) -> tuple[list[str], float]:
    """Write a letter and its sign with room between them and before the next letter.

    Parameters
    ----------
    cluster : str
        A cluster from :func:`sign_clusters`, such as ``"മൃ"``.
    glyph_data : dict
        Jayasree's ``glyph-data.json``.
    atoms : dict
        The chosen strokes, ``{cluster: {"strokes": [...]}}``.
    baked : dict
        Every cluster baked so far, which holds the letter's strokes.

    Returns
    -------
    tuple[list[str], float]
        The letter's strokes, then the sign's, slid left until ``SIGN_CLEARANCE`` from the letter's,
        and the width the cluster needs: the sign's right edge plus ``ATOM_GAP`` (at least its own).
    """
    base, sign = cluster[:-1], cluster[-1]
    base_strokes = [s["d"] for s in baked[base]["strokes"]]
    base_pts = bfs._sample(base_strokes)
    sign_pts = bfs._sample([s["d"] for s in atoms[sign]["strokes"]])
    # start clear of the base, then slide the sign left until it is SIGN_CLEARANCE from the base
    shift = base_pts[:, 0].max() + SIGN_CLEARANCE - sign_pts[:, 0].min()
    while shift > -4000 and _distance(base_pts, sign_pts + np.array([shift - SLIDE, 0.0])) >= (
        SIGN_CLEARANCE
    ):
        shift -= SLIDE
    matrix = (1.0, 0.0, 0.0, 1.0, shift, 0.0)
    moved = [bfs.path_d(s["d"], matrix) for s in atoms[sign]["strokes"]]
    right = max(parse_path(d).bbox()[1] for d in moved)
    return base_strokes + moved, max(right + ATOM_GAP, glyph_data["clusters"][cluster]["advance"])


def main() -> None:
    """Add a "Stitched" option to the candidates of every target cluster that can be stitched."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", type=Path, default=bfs.CANDIDATES)
    ap.add_argument("--choices", type=Path, default=bfs.CHOICES)
    ap.add_argument(
        "--min-cover",
        type=float,
        default=MIN_COVER,
        help="the least share of ink the letters must cover",
    )
    ap.add_argument("--targets", type=Path, help="a file of clusters to stitch, one per line")
    args = ap.parse_args()
    glyphs = json.loads(bfs.GLYPH_DATA.read_text("utf-8"))
    candidates = json.loads(args.candidates.read_text("utf-8"))
    choices = json.loads(args.choices.read_text("utf-8"))
    atoms = bfs.build(candidates, choices, glyphs)
    if args.targets:
        # clusters named here are stitched even if they are already chosen
        targets = args.targets.read_text("utf-8").split()
    else:
        targets = [c for c in candidates if c not in atoms]
    fields: dict = {}
    done = 0
    for cluster in targets:
        strokes, share, note = stitch_cluster(cluster, glyphs, atoms, fields, args.min_cover)
        print(f"{cluster}\t{note}" + (f" ({share:.0%})" if strokes else ""), flush=True)
        if strokes:
            candidates.setdefault(cluster, {})[STITCHED] = strokes
            done += 1
        else:
            candidates.get(cluster, {}).pop(STITCHED, None)
    args.candidates.write_text(
        json.dumps(candidates, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{done} of {len(targets)} clusters stitched -> {args.candidates}")


if __name__ == "__main__":
    main()
