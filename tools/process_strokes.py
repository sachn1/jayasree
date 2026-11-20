#!/usr/bin/env python3
"""Unified stroke-processing pipeline: center, smooth, straighten, expand.

Replaces the earlier separate snap_strokes.py / straighten_lines.py /
refine_with_ghost.py / center_strokes_v2.py / expand_combinations.py scripts
(and their six intermediate/duplicate output files) with one configurable
pass over the hand-authored js/src/stroke-data.raw.json, writing a single
UI-ready file: js/src/stroke-data.json - the name index.js's loadStrokes()
already defaults to fetching, and the file demo.js loads. Re-running this
script always refreshes that one file in place, so it's always the latest
processed version; js/src/stroke-data.raw.json (edited by
tools/stroke-recorder.html) is untouched, so re-processing with different
flags is always possible without re-recording anything.

Stages (each independently toggleable):
  --center      Gradient-ascent centering onto the glyph's ink ridge
                (jayasree.centering)
  --smooth      Corner-aware piecewise spline fit - the baseline cleanup
                (jayasree.geometry)
  --straighten  Ghost-guided angle correction: straight runs are matched
                against reference segments derived from the font outline
                and rotated to the font's exact angle
                (jayasree.ghost_reference)
  --expand      Per-glyph composition: a cluster where every individual
                character already has its own authored stroke gets one
                composed from them (jayasree.stroke_compose).
                Mark composition (consonant+virama, conjunct+matra,
                subjoined conjunct forms) is *not* done here - it happens
                at runtime in js/src/index.js instead, so stroke-data.json
                doesn't pre-bake a candidate for every base times every
                mark regardless of whether it's ever traced.

--preset=full (or its historical alias --preset=malayalam) enables all four
stages - script-agnostic, despite the alias's name; pass explicit
--center/--no-center etc. to override any of them.

--lang selects which language's default --input/--glyph-data/--output paths
to use (jayasree.languages.LANGUAGES; default: malayalam) - pass explicit
--input/--glyph-data/--output to override any of them individually. Before
any stage runs, a `lang.code`-gated block may synthesize some clusters'
strokes from others already hand-traced (e.g. Hindi's `_hi_derive_strokes()`
below, for its decomposable nukta consonants) instead of requiring a second
human trace - same gated-by-language-code convention as every other
language-specific quirk in this project, never a private mechanism. Never
overrides a cluster stroke-data.raw.json already genuinely has.

Usage (from repo root):
    python tools/process_strokes.py --preset=full
    python tools/process_strokes.py --smooth --expand   # no centering/straightening
    python tools/process_strokes.py --preset=full --lang tamil
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

from jayasree import centering, geometry, ghost_reference, stroke_compose  # noqa: E402
from jayasree.languages import data_paths, get_language  # noqa: E402

N_SAMPLES = 120  # arc-length-uniform points sampled per stroke before center/smooth

#: Curve-straightening (ghost_reference's circle-matching) is a separate,
#: still-unfinished feature from the sparse-piece smoothing fix below -
#: confirmed via real testing to still introduce its own splice-boundary
#: artifacts (see docs/CENTERING_EXPERIMENTS.md's "Curve straightening"
#: section, "Still open when this was paused"). Deliberately its own
#: switch, not folded into any `lang_code == "hi"` check - the two are
#: unrelated fixes that happen to both touch Hindi, and gating them
#: together was itself a bug (flipping this on by accident reintroduced
#: jagged output immediately after the smoothing fix had just cleaned it
#: up). Flip to True only once that section's open tangent-continuity
#: problem is actually resolved and visually verified.
_CURVE_STRAIGHTEN_ENABLED = False

_ALL_STAGES: dict[str, bool] = {"center": True, "smooth": True, "straighten": True, "expand": True}
PRESETS: dict[str, dict[str, bool]] = {
    "malayalam": _ALL_STAGES,  # historical name from this project's first language - kept
    # working for existing docs/scripts (and the Malayalam freeze); prefer "full" below for
    # anything new, since these four stages are entirely script-agnostic.
    "full": _ALL_STAGES,
}


def parse_args() -> argparse.Namespace:
    """Parse CLI args, resolving `--preset`/`--lang` defaults for anything left unset.

    Returns
    -------
    argparse.Namespace
        Parsed arguments, with every stage flag (``center``, ``smooth``,
        ``straighten``, ``expand``) resolved to an explicit bool, and
        ``input``/``glyph_data``/``output`` resolved to concrete paths.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--preset", choices=sorted(PRESETS), help="Apply a named default set of stages"
    )
    parser.add_argument("--center", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--smooth", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--straighten", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--expand", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--lang",
        default="malayalam",
        help="Registry key from jayasree.languages.LANGUAGES - selects default "
        "--input/--glyph-data/--output paths (default: malayalam).",
    )
    parser.add_argument(
        "--input", type=Path, default=None, help="Defaults to --lang's stroke-data.raw.json"
    )
    parser.add_argument(
        "--glyph-data",
        type=Path,
        default=None,
        dest="glyph_data",
        help="Defaults to --lang's glyph-data.json",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Defaults to --lang's stroke-data.json"
    )
    args = parser.parse_args()

    try:
        lang = get_language(args.lang)
    except ValueError as exc:
        parser.error(str(exc))
    lang_paths = data_paths(lang)
    args.input = args.input or lang_paths.stroke_data_raw
    args.glyph_data = args.glyph_data or lang_paths.glyph_data
    args.output = args.output or lang_paths.stroke_data

    preset = PRESETS.get(args.preset, {})
    for stage in ("center", "smooth", "straighten", "expand"):
        if getattr(args, stage) is None:
            setattr(args, stage, preset.get(stage, False))
    return args


def _reference_glyphs(cluster: str, cluster_info: dict, marks: dict) -> list[dict]:
    """Return the glyphs to use as the centering/straightening reference for `cluster`.

    A mark's own standalone entry includes HarfBuzz's dotted-circle
    placeholder (see tools/build_glyph_data.py's ``_standalone_inputs()``)
    alongside its real content glyph - the human only traced the content, so
    the placeholder must be excluded here, or it corrupts the distance field
    with a second, spurious "ink" blob the gradient ascent can wander into
    (shows up as wiggle right where the content starts, next to where the
    circle would have been). ``marks`` already knows, per mark, whether
    content is glyphs[0] (prefix marks, which render before the circle) or
    glyphs[-1] (suffix marks, circle first) - see ``_build_marks()``'s
    docstring in build_glyph_data.py.

    Gated on glyph count + a `marks` entry rather than `len(cluster) == 1`:
    ്ര is a 2-codepoint mark (VIRAMA + "ര") with this exact same
    circle+content shape once it's in `_standalone_inputs()` - a
    single-codepoint-only check would silently skip the exclusion for it
    and corrupt its reference field the same way.
    """
    glyphs = cluster_info["glyphs"]
    if len(glyphs) != 2:
        return glyphs
    mark = marks.get(cluster)
    if not mark:
        return glyphs
    return [glyphs[0]] if mark["prefix"] else [glyphs[-1]]


def _process_stroke(
    d: str,
    field: centering.DistField | None,
    refs: list[dict],
    args: argparse.Namespace,
    lang_code: str,
    curve_refs: list[dict] | None = None,
) -> str:
    """Run one stroke through the center/smooth/straighten stages, in that order.

    `lang_code` gates Hindi-only fixes directly in code (`lang_code == "hi"`),
    the same way every other per-language quirk in this project is gated
    (see tools/build_glyph_data.py) - never a configurable default any
    language could inherit by omission. Malayalam's own path through this
    function never evaluates to anything but the plain, original behavior.
    """
    if args.center or args.smooth:
        pts = geometry.sample_path(d, N_SAMPLES)
        if len(pts) >= 4:
            if args.center and field is not None:
                pts = centering.center_points(pts, field)
            if args.smooth:
                # Hindi-only: re-fit an RDP-over-simplified piece from its
                # real points instead of leaving it too sparse to curve
                # through - see geometry.smooth_points's
                # `sparse_piece_fallback` docstring for the confirmed bug
                # this fixes (docs/CENTERING_EXPERIMENTS.md's "Curve
                # straightening" section). Malayalam's call below never
                # passes this - its own already-approved, snapshot-gated
                # output is untouched by construction, not by a default.
                smoothed = geometry.smooth_points(pts, sparse_piece_fallback=(lang_code == "hi"))
                if smoothed:
                    d = smoothed
            else:
                # Centered but not smoothed: emit a raw polyline through the
                # moved points rather than silently dropping the centering.
                d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)

    if args.straighten and refs:
        d = ghost_reference.refine_stroke(
            d,
            refs,
            curve_refs if _CURVE_STRAIGHTEN_ENABLED else None,
            # Hindi-only: reject a reference segment too short to actually
            # represent the piece being matched - see
            # ghost_reference.REF_LENGTH_MATCH_RATIO's docstring for the
            # confirmed bug this fixes (a long curved "bridge" stroke
            # collapsing onto an unrelated short straight edge) and why
            # it's opt-in rather than on by default (367 of Malayalam's
            # 1721 already-committed clusters change if enabled
            # unconditionally - Malayalam's own call here never passes
            # this, so its output is untouched by construction).
            ghost_reference.REF_LENGTH_MATCH_RATIO if lang_code == "hi" else 0.0,
        )

    return d


#: Of Hindi's 7 nukta consonants, these 5 are verified (byte-identical first
#: SVG subpath against the plain base consonant - see
#: tools/build_glyph_data.py's `_HI_DECOMPOSABLE_NUKTA_BASE` docstring,
#: duplicated here rather than imported across these two standalone scripts)
#: to be exactly their base consonant's own outline plus one small
#: additional dot contour at a font-given position - genuinely decomposable.
#: ख़/फ़ are deliberately excluded: Noto draws a genuinely different base
#: shape for those two, same category as a true akhand ligature.
_HI_DECOMPOSABLE_NUKTA_BASE: dict[str, str] = {
    chr(0x958): "क",
    chr(0x95A): "ग",
    chr(0x95B): "ज",
    chr(0x95C): "ड",
    chr(0x95D): "ढ",
}

_HI_NUKTA_MARK = "़"
_HI_SUBPATH_RE = re.compile(r"M[^M]*")
_HI_COORD_RE = re.compile(r"-?\d+\.?\d*")


def _hi_path_bbox_center(d: str) -> tuple[float, float]:
    """Rough bounding-box center of every x/y coordinate pair in `d`.

    Deliberately crude (treats curve control points the same as
    endpoints) - good enough for this function's one use: locating a
    small, near-circular dot's position well enough to compute a
    translation offset, not a general SVG bbox calculator.
    """
    nums = [float(n) for n in _HI_COORD_RE.findall(d)]
    xs, ys = nums[0::2], nums[1::2]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def _hi_derive_strokes(stroke_data: dict, shaped_clusters: dict) -> dict:
    """Synthesize Hindi's 5 decomposable nukta consonants' strokes, if derivable.

    Reuses two already-recorded things verbatim, never asking for a second
    human trace:

    1. The plain base consonant's own recorded strokes, as-is - its outline
       is byte-identical inside the fused nukta glyph (see
       `_HI_DECOMPOSABLE_NUKTA_BASE` above), so no translation is needed for
       this part; same coordinate frame already.
    2. The nukta mark's (़, U+093C) own recorded stroke(s) - Hindi's Group B
       synthetic atom (docs/languages/hi/README.md) - translated from
       wherever it was drawn to the exact position this specific nukta
       consonant's real shaped outline puts its dot (`shaped_clusters[nukta_
       char]`'s last SVG subpath), using `stroke_compose.offset_svg_path`
       (the same helper reph/half-form composition already uses).

    Only fires once *both* dependencies (the base consonant, the nukta
    mark) have real recorded strokes, and never overrides a nukta consonant
    that already has its own real entry - the caller only uses
    `dict.setdefault`.

    Parameters
    ----------
    stroke_data : dict
        The hand-authored stroke-data.raw.json content.
    shaped_clusters : dict
        glyph-data.hi.json's own `clusters` - this build's real HarfBuzz
        output, consulted only to locate each fused glyph's real dot
        subpath, never to invent geometry the font doesn't actually have.

    Returns
    -------
    dict
        ``{nukta_consonant: {"strokes": [...]}}`` for whichever of the 5
        have both dependencies recorded.
    """
    mark_entry = stroke_data.get(_HI_NUKTA_MARK)
    if not mark_entry or not mark_entry.get("strokes"):
        return {}
    mark_strokes = mark_entry["strokes"]
    mark_center = _hi_path_bbox_center(mark_strokes[0]["d"])

    derived: dict = {}
    for nukta_char, base_char in _HI_DECOMPOSABLE_NUKTA_BASE.items():
        base_entry = stroke_data.get(base_char)
        fused = shaped_clusters.get(nukta_char)
        if not base_entry or not base_entry.get("strokes") or not fused:
            continue
        dot_d = _HI_SUBPATH_RE.findall(fused["glyphs"][0]["d"])[-1]
        dot_center = _hi_path_bbox_center(dot_d)
        dx, dy = dot_center[0] - mark_center[0], dot_center[1] - mark_center[1]
        dot_strokes = [{"d": stroke_compose.offset_svg_path(s["d"], dx, dy)} for s in mark_strokes]
        derived[nukta_char] = {"strokes": [*base_entry["strokes"], *dot_strokes]}
    return derived


def _process_cluster_strokes(
    cluster: str, entry: dict, glyph_data: dict, args: argparse.Namespace, lang_code: str
) -> list[dict]:
    """Run one hand-recorded cluster's strokes through the stages `args` enables.

    For a cluster the glyph data knows, the stages are guided by that cluster's own font outline
    (its distance field, and the straight edges detected on it); for one it does not know, only
    the stages that need no outline run. This is the per-cluster body of :func:`main`, kept as one
    function so that the Malayalam freeze test (``python/tests/test_malayalam_freeze.py``) runs
    exactly the code `main()` runs, not a copy that could drift from it.

    Parameters
    ----------
    cluster : str
        The cluster's key in the stroke data.
    entry : dict
        Its ``{"strokes": [{"d": ...}, ...]}`` as recorded.
    glyph_data : dict
        The language's parsed ``glyph-data.json`` (``clusters`` and, optionally, ``marks``).
    args : argparse.Namespace
        Which stages run (``center``, ``smooth``, ``straighten``).
    lang_code : str
        The language's code, for the inline per-language gates in :func:`_process_stroke`.

    Returns
    -------
    list[dict]
        The processed strokes, ``[{"d": ...}, ...]``, in recorded order.
    """
    cluster_info = glyph_data["clusters"].get(cluster)

    field = None
    refs: list[dict] = []
    curve_refs: list[dict] = []
    if (args.center or args.straighten) and cluster_info is not None:
        ref_glyphs = _reference_glyphs(cluster, cluster_info, glyph_data.get("marks", {}))
        field = centering.make_dist_field(ref_glyphs)
        if args.straighten:
            refs = ghost_reference.build_reference_segments(ref_glyphs, field)
            if _CURVE_STRAIGHTEN_ENABLED:
                curve_refs = ghost_reference.build_curve_reference_segments(ref_glyphs, field)

    return [
        {"d": _process_stroke(s["d"], field, refs, args, lang_code, curve_refs)}
        for s in entry.get("strokes", [])
    ]


def main() -> None:
    """Run the requested stages over `stroke-data.raw.json` and write the output file."""
    args = parse_args()
    args.input = args.input.resolve()
    args.output = args.output.resolve()
    if not (args.center or args.smooth or args.straighten or args.expand):
        print(
            "Nothing to do - pass --preset=full or at least one stage flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    stroke_data: dict = json.loads(args.input.read_text(encoding="utf-8"))
    glyph_data: dict = json.loads(args.glyph_data.read_text(encoding="utf-8"))
    clusters = glyph_data["clusters"]

    # Resolved once, reused for every `lang_code == "hi"` gate below - same
    # inline per-language-code gating this project already uses throughout
    # tools/build_glyph_data.py, never a configurable default any language
    # could inherit by omission.
    lang_code = get_language(args.lang).code

    # A language may be able to derive some clusters' strokes from others
    # already hand-traced (e.g. Hindi's nukta consonants - see
    # `_hi_derive_strokes()` above) rather than needing a second human
    # trace. Merged in before the main loop so centering/straightening
    # apply to derived strokes exactly like any other recorded one, against
    # that cluster's own real font reference - never overrides a cluster
    # that's already genuinely present.
    if lang_code == "hi":
        for cluster, entry in _hi_derive_strokes(stroke_data, clusters).items():
            stroke_data.setdefault(cluster, entry)

    out: dict = {}

    for cluster, entry in stroke_data.items():
        # "_remarks" (tools/stroke-recorder.js's authoring-time notes on why
        # a cluster was skipped / what it might compose from - see
        # tools/validate_data.py's RESERVED_STROKE_DATA_KEYS, duplicated
        # here rather than imported per that module's dependency-free
        # docstring) is metadata for a human/agent reviewer, never runtime
        # data - drop it instead of emitting a bogus "_remarks" cluster.
        if cluster == "_remarks":
            continue
        strokes = _process_cluster_strokes(cluster, entry, glyph_data, args, lang_code)
        out[cluster] = {"strokes": strokes}

    if args.expand:
        out, generated, skipped = stroke_compose.compose_all(glyph_data, out)
        print(f"Expansion: generated {generated} composed clusters, {skipped} skipped")

    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    stages = [s for s in ("center", "smooth", "straighten", "expand") if getattr(args, s)]
    try:
        output_display = args.output.relative_to(ROOT)
    except ValueError:
        output_display = args.output
    print(f"Stages: {', '.join(stages) or 'none'}")
    print(f"Written {output_display} ({len(out)} clusters)")


if __name__ == "__main__":
    main()
