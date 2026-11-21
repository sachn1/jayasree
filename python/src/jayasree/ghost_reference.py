"""Build straight reference segments from a glyph's ghost outline, in centerline space."""

from __future__ import annotations

import re

import numpy as np
import svgpathtools

from .centering import DistField, center_points
from .geometry import CORNER_ANGLE_DEG, smooth_points

N_GHOST_SAMPLES_PER_UNIT: float = 0.3  # ghost outline sampling density (pts per font unit)
STRAIGHT_TOLERANCE: float = 5.0  # max deviation (fu) for an outline edge to count as "straight"
STRAIGHT_MIN_LENGTH: float = 50.0  # min length (fu) for an outline edge segment

REF_MIN_LENGTH: float = 60.0  # ignore outline edges too short to trust as a reference
REF_MAX_RESIDUAL: float = 30.0  # max fu deviation from a straight line after ascent

# -- Hand-drawn stroke: corner splitting + straight-run matching --
STRAIGHT_RESIDUAL_TOLERANCE: float = 15.0  # max fu deviation for a "meant to be straight" piece
MIN_STRAIGHT_PIECE_LENGTH: float = 40.0  # ignore tiny nubs
ANGLE_MATCH_TOLERANCE_DEG: float = 22.0
DIST_MATCH_TOLERANCE: float = 45.0
#: A reference segment represents one *specific bounded stretch* of the
#: font's own outline - but match_reference's angle/perpendicular-distance
#: check treats it as an infinite line, with nothing tying the match back
#: to the reference's own extent. A long, gently-curving hand-drawn piece
#: can pass the residual check (STRAIGHT_RESIDUAL_TOLERANCE is absolute,
#: not relative to length) and then "match" a much shorter reference
#: segment that merely happens to share its rough angle, getting rigidly
#: rotated onto it - collapsing a real curve into a near-straight line
#: (confirmed directly: ञ's own 3rd recorded stroke - a 541fu
#: gently-curving run - matched a 68fu vertical reference this way).
#: Requires the reference to be at least this fraction of the piece's own
#: length - generous enough that a piece legitimately overshooting past
#: where a short reference edge ends still matches, but rejects a
#: reference an order of magnitude shorter than what it's being asked to
#: represent.
#:
#: Opt-in only (`match_reference`'s `min_length_ratio` defaults to 0.0,
#: i.e. disabled) - turning this on unconditionally changes 367 of
#: Malayalam's 1721 already-published clusters, which is exactly the kind
#: of already-approved-data change this project requires discussing
#: explicitly rather than folding into a routine fix. `tools/
#: process_strokes.py` passes this value only for `lang_code == "hi"`,
#: same gating convention as `geometry.smooth_points`'s
#: `sparse_piece_fallback`.
REF_LENGTH_MATCH_RATIO: float = 0.5

# -- Curved outline edges / hand-drawn arcs (opt-in via --curve-straighten) --
# Same two-sided shape as the straight-line constants above: one set of
# tolerances for what counts as a trustworthy *reference* arc extracted from
# the font's own outline, one set for what counts as a "meant to be a smooth
# arc" hand-drawn piece, and a separate match tolerance between the two -
# mirrors the straight-line design throughout, not a new philosophy.
CURVE_TOLERANCE: float = 6.0  # max deviation (fu) for an outline edge to count as circular
CURVE_MIN_LENGTH: float = 50.0  # min chord length (fu) for a candidate curved outline edge
MAX_CURVE_RADIUS: float = 2000.0  # above this, a "circle" is indistinguishable from a straight line

CURVE_REF_MIN_LENGTH: float = 50.0  # ignore outline arcs too short to trust as a reference
CURVE_REF_MAX_RESIDUAL: float = 25.0  # max fu deviation from a circle after ascent

CURVE_PIECE_RESIDUAL_TOLERANCE: float = 18.0  # max fu deviation for a "meant to be smooth" piece
MIN_CURVE_PIECE_LENGTH: float = 40.0  # ignore tiny nubs, same bar as the straight case
RADIUS_MATCH_RATIO_TOLERANCE: float = 0.35  # |r_piece - r_ref| / r_ref must be below this
CURVE_CENTER_MATCH_TOLERANCE: float = 60.0  # max fu between a piece's and a reference's own center


def sample_outline(glyph_glyphs: list[dict]) -> list[np.ndarray]:
    """Sample points along each ghost outline contour.

    Parameters
    ----------
    glyph_glyphs : list[dict]
        Glyph components, each with ``d`` (SVG path), ``x``, ``y``.

    Returns
    -------
    list[np.ndarray]
        One ``(n, 2)`` array of sampled points per outline contour.
    """
    contours = []
    for comp in glyph_glyphs:
        dx, dy = comp.get("x", 0), comp.get("y", 0)
        for sub_d in re.findall(r"M[^M]*", comp["d"]):
            try:
                sub = svgpathtools.parse_path(sub_d)
            except Exception:
                continue
            length = sub.length()
            if length <= 0:
                continue
            n_pts = max(50, int(length * N_GHOST_SAMPLES_PER_UNIT))
            pts = []
            for i in range(n_pts + 1):
                p = sub.point(i / n_pts)
                pts.append([p.real + dx, p.imag + dy])
            contours.append(np.array(pts))
    return contours


def find_straight_segments(contours: list[np.ndarray]) -> list[dict]:
    """Find straight edge segments in the raw ghost outline (boundary space).

    Parameters
    ----------
    contours : list[np.ndarray]
        Sampled outline contours, as returned by :func:`sample_outline`.

    Returns
    -------
    list[dict]
        One entry per straight edge found, each with ``start``, ``end``
        (points) and ``length`` (float).
    """
    segments = []
    for contour in contours:
        n = len(contour)
        if n < 5:
            continue

        i = 0
        while i < n - 3:
            best_end = -1
            for j in range(i + 3, min(i + n // 2, n)):
                chord = contour[j] - contour[i]
                chord_len = np.linalg.norm(chord)
                if chord_len < 1e-6:
                    continue
                delta = contour[i + 1 : j] - contour[i]
                perp_dist = np.abs(chord[0] * delta[:, 1] - chord[1] * delta[:, 0]) / chord_len
                if np.max(perp_dist) <= STRAIGHT_TOLERANCE:
                    if chord_len >= STRAIGHT_MIN_LENGTH:
                        best_end = j
                else:
                    break

            if best_end >= 0:
                start_pt = contour[i]
                end_pt = contour[best_end]
                length = np.linalg.norm(end_pt - start_pt)
                segments.append({"start": start_pt, "end": end_pt, "length": length})
                i = best_end
            else:
                i += 1

    return segments


def fit_line(
    pts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Fit the best line through points via PCA.

    Parameters
    ----------
    pts : np.ndarray
        Points to fit, shape ``(n, 2)``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, float, float, float]
        ``(mean, unit_direction, max_perp_residual, proj_min, proj_max)``:
        the line's mean point, unit direction vector, the largest
        perpendicular deviation from it, and the min/max projection of
        `pts` onto that direction (the line's extent).
    """
    mean = pts.mean(axis=0)
    centered = pts - mean
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    direction = vt[0]
    direction = direction / np.linalg.norm(direction)
    proj = centered @ direction
    perp = centered - np.outer(proj, direction)
    residual = float(np.max(np.linalg.norm(perp, axis=1))) if len(perp) else 0.0
    return mean, direction, residual, float(proj.min()), float(proj.max())


def fit_circle(pts: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Fit the best circle through points via the Kåsa algebraic least-squares method.

    Standard technique: a circle `(x-a)² + (y-b)² = r²` expands to the linear
    form `2ax + 2by + (r² - a² - b²) = x² + y²`, solvable directly via
    `np.linalg.lstsq` - same "fit the simplest shape that explains these
    points, then measure how well it actually does" spirit as
    :func:`fit_line`, just for the other shape a pen stroke commonly is.

    Parameters
    ----------
    pts : np.ndarray
        Points to fit, shape ``(n, 2)``.

    Returns
    -------
    tuple[np.ndarray, float, float]
        ``(center, radius, max_residual)`` - the fitted circle's center,
        radius, and the largest deviation of any point from that exact
        radius (the circular analogue of `fit_line`'s perpendicular
        residual).
    """
    x, y = pts[:, 0], pts[:, 1]
    coeffs = np.column_stack([2 * x, 2 * y, np.ones(len(pts))])
    rhs = x**2 + y**2
    sol, *_ = np.linalg.lstsq(coeffs, rhs, rcond=None)
    a, c, d = sol
    center = np.array([a, c])
    radius = float(np.sqrt(d + a**2 + c**2)) if d + a**2 + c**2 > 0 else float("inf")
    residual = float(np.max(np.abs(np.linalg.norm(pts - center, axis=1) - radius)))
    return center, radius, residual


def find_curved_segments(
    contours: list[np.ndarray],
    tolerance: float = CURVE_TOLERANCE,
    min_length: float = CURVE_MIN_LENGTH,
    max_radius: float = MAX_CURVE_RADIUS,
) -> list[dict]:
    """Find circular-arc runs within one or more point sequences.

    Mirrors :func:`find_straight_segments` exactly - a growing window per
    input array, kept as long as it stays within tolerance of *some*
    circle - just with a circle-fit residual test (:func:`fit_circle`)
    instead of a straight-line one, and a radius ceiling (`max_radius`) to
    exclude near-straight runs a circle fit would otherwise also accept (a
    straight line is a circle of infinite radius).

    Dual use, via the tolerance/min_length/max_radius defaults: called with
    font-outline tolerances (the module-level `CURVE_*` constants, this
    function's defaults) on a ghost outline's sampled contours by
    :func:`build_curve_reference_segments`, and called again with the
    looser hand-drawn-stroke tolerances (`CURVE_PIECE_RESIDUAL_TOLERANCE`/
    `MIN_CURVE_PIECE_LENGTH`) on a single piece's own sampled points by
    :func:`refine_stroke` - a hand-drawn compound curve (e.g. a consonant's
    loop blending into a stem) is rarely one clean circle end to end the
    way a short font-outline edge usually is, so fitting *one* circle to
    the whole piece is too coarse; this finds whichever *sub-runs* of it
    are circular instead, the same way it already finds circular runs
    within a longer outline contour.

    Parameters
    ----------
    contours : list[np.ndarray]
        One or more point sequences to scan - ghost-outline contours (as
        returned by :func:`sample_outline`) in the outline-detection case,
        or a single hand-drawn piece's own sampled points (wrapped in a
        one-element list) in the piece-detection case.
    tolerance : float, optional
        Max circle-fit residual (font units) for a window to still count
        as circular.
    min_length : float, optional
        Min chord length (font units) for a candidate run.
    max_radius : float, optional
        Radius ceiling excluding near-straight runs.

    Returns
    -------
    list[dict]
        One entry per curved run found, each with ``points`` (the sampled
        points spanning it), ``i0``/``i1`` (its start/end index within its
        own input array - meaningful only when `contours` has exactly one
        element, the piece-detection case) and ``length`` (chord, float).
    """
    segments = []
    for contour in contours:
        n = len(contour)
        if n < 8:
            continue

        i = 0
        while i < n - 6:
            best_end = -1
            for j in range(i + 6, min(i + n // 2, n)):
                window = contour[i : j + 1]
                _, radius, residual = fit_circle(window)
                if residual <= tolerance and radius <= max_radius:
                    chord_len = float(np.linalg.norm(contour[j] - contour[i]))
                    if chord_len >= min_length:
                        best_end = j
                else:
                    break

            if best_end >= 0:
                segments.append(
                    {
                        "points": contour[i : best_end + 1],
                        "i0": i,
                        "i1": best_end,
                        "length": float(np.linalg.norm(contour[best_end] - contour[i])),
                    }
                )
                i = best_end
            else:
                i += 1

    return segments


def build_curve_reference_segments(glyph_glyphs: list[dict], field: DistField) -> list[dict]:
    """Build circular-arc reference segments in centerline space.

    Direct curved-shape counterpart to :func:`build_reference_segments` -
    same method (sample the outline edge, gradient-ascend into the ink,
    fit the target shape, discard anything with high residual - ascent
    wandering near a corner/junction shows up as exactly that), just
    fitting a circle instead of a line.

    Parameters
    ----------
    glyph_glyphs : list[dict]
        Glyph components, each with ``d`` (SVG path), ``x``, ``y``.
    field : DistField
        The glyph's distance-transform field to ascend into.

    Returns
    -------
    list[dict]
        Reference arcs, each with ``center``, ``radius`` and ``length``.
    """
    if field.ink_tree is None:
        return []

    contours = sample_outline(glyph_glyphs)
    outer_segments = find_curved_segments(contours)

    refs = []
    for seg in outer_segments:
        if seg["length"] < CURVE_REF_MIN_LENGTH:
            continue
        pts = seg["points"]
        n_sample = max(6, int(seg["length"] / 40))
        idx = np.linspace(0, len(pts) - 1, n_sample).astype(int)
        ascended = center_points(pts[idx], field, max_shift_fu=float("inf"))

        center, radius, residual = fit_circle(ascended)
        if residual > CURVE_REF_MAX_RESIDUAL or radius > MAX_CURVE_RADIUS:
            continue

        refs.append({"center": center, "radius": radius, "length": seg["length"]})
    return refs


def build_reference_segments(glyph_glyphs: list[dict], field: DistField) -> list[dict]:
    """Build straight reference segments in centerline space.

    Each outer straight outline edge is sampled and gradient-ascended into
    the ink (:func:`~jayasree.centering.center_points`); a line fit
    through the ascended points is kept only if it's clean (low residual) -
    this discards edges near corners/junctions where ascent can wander to
    the wrong local ridge.

    Parameters
    ----------
    glyph_glyphs : list[dict]
        Glyph components, each with ``d`` (SVG path), ``x``, ``y``.
    field : DistField
        The glyph's distance-transform field to ascend into.

    Returns
    -------
    list[dict]
        Reference segments, each with ``start``, ``end``, ``direction``
        (unit vector), ``angle`` (degrees, mod 180) and ``length``.
    """
    if field.ink_tree is None:
        return []

    contours = sample_outline(glyph_glyphs)
    outer_segments = find_straight_segments(contours)

    refs = []
    for seg in outer_segments:
        if seg["length"] < REF_MIN_LENGTH:
            continue
        n_sample = max(6, int(seg["length"] / 40))
        chord = seg["end"] - seg["start"]
        sample_pts = np.array([seg["start"] + t * chord for t in np.linspace(0.15, 0.85, n_sample)])
        ascended = center_points(sample_pts, field, max_shift_fu=float("inf"))

        mean, direction, residual, pmin, pmax = fit_line(ascended)
        length = pmax - pmin
        if residual > REF_MAX_RESIDUAL or length < REF_MIN_LENGTH * 0.5:
            continue

        angle = np.degrees(np.arctan2(direction[1], direction[0])) % 180
        refs.append(
            {
                "start": mean + direction * pmin,
                "end": mean + direction * pmax,
                "direction": direction,
                "angle": angle,
                "length": length,
            }
        )
    return refs


# ---------------------------------------------------------------------------
# Hand-drawn stroke: corner splitting + straight-run matching
# ---------------------------------------------------------------------------


def split_path_into_pieces(path: svgpathtools.Path) -> list[list]:
    """Group path segments into corner-free pieces via tangent-angle breaks.

    Mirrors the corner detection in :mod:`jayasree.geometry`, but
    works directly off the parsed segments' tangents rather than resampled
    points - the corner is already a real geometric feature of the smoothed
    path (a tangent break between two pieces), not something that needs
    re-inferring.

    Parameters
    ----------
    path : svgpathtools.Path
        Parsed SVG path to split.

    Returns
    -------
    list[list]
        One list of consecutive path segments per corner-free piece.
    """
    if len(path) == 0:
        return []
    pieces = [[path[0]]]
    for i in range(1, len(path)):
        d_prev = path[i - 1].derivative(1.0)
        d_cur = path[i].derivative(0.0)
        if abs(d_prev) < 1e-9 or abs(d_cur) < 1e-9:
            angle = 0.0
        else:
            cosang = (d_prev.real * d_cur.real + d_prev.imag * d_cur.imag) / (
                abs(d_prev) * abs(d_cur)
            )
            cosang = max(-1.0, min(1.0, cosang))
            angle = np.degrees(np.arccos(cosang))
        if angle > CORNER_ANGLE_DEG:
            pieces.append([path[i]])
        else:
            pieces[-1].append(path[i])
    return pieces


def sample_piece(segs: list, n: int = 30) -> np.ndarray:
    """Sample n arc-length-uniform points along a piece's parsed path segments.

    Parameters
    ----------
    segs : list
        Consecutive parsed path segments forming one corner-free piece.
    n : int, optional
        Number of equally-spaced samples.

    Returns
    -------
    np.ndarray
        Array of shape ``(n, 2)`` with ``(x, y)`` coordinates, or a
        single-point array if the piece has zero length.
    """
    sub = svgpathtools.Path(*segs)
    length = sub.length()
    if length <= 0:
        p = segs[0].start
        return np.array([[p.real, p.imag]])
    pts = []
    for i in range(n):
        s = i / (n - 1) * length
        try:
            t = sub.ilength(s)
        except Exception:
            t = i / (n - 1)
        p = sub.point(t)
        pts.append([p.real, p.imag])
    return np.array(pts)


def match_reference(
    piece_pts: np.ndarray,
    piece_direction: np.ndarray,
    refs: list[dict],
    min_length_ratio: float = 0.0,
) -> dict | None:
    """Find the best reference segment matching a straight hand-drawn run, if any.

    Parameters
    ----------
    piece_pts : np.ndarray
        Sampled points of the hand-drawn straight run, shape ``(n, 2)``.
    piece_direction : np.ndarray
        Unit direction vector of the run, as fit by :func:`fit_line`.
    refs : list[dict]
        Candidate reference segments, as returned by
        :func:`build_reference_segments`.
    min_length_ratio : float
        Reject a reference shorter than this fraction of the piece's own
        length (see :data:`REF_LENGTH_MATCH_RATIO`'s docstring for why).
        Defaults to ``0.0`` (disabled, i.e. every existing caller/committed
        cluster keeps the exact behavior this function always had,
        byte-for-byte) - `tools/process_strokes.py` opts a language in by
        passing :data:`REF_LENGTH_MATCH_RATIO` explicitly, the same
        `lang_code`-gated pattern as `geometry.smooth_points`'s
        `sparse_piece_fallback`. Confirmed this genuinely changes output
        for already-committed Malayalam clusters (367 of 1721) if enabled
        unconditionally - not something to flip on by default without
        that being an explicit, discussed decision.

    Returns
    -------
    dict | None
        The closest matching reference segment within tolerance, or
        ``None`` if none match.
    """
    piece_angle = np.degrees(np.arctan2(piece_direction[1], piece_direction[0])) % 180
    piece_proj = piece_pts @ piece_direction
    piece_length = float(piece_proj.max() - piece_proj.min())
    best, best_dist = None, None
    for ref in refs:
        da = abs(piece_angle - ref["angle"])
        da = min(da, 180 - da)
        if da > ANGLE_MATCH_TOLERANCE_DEG:
            continue
        if ref["length"] < piece_length * min_length_ratio:
            continue
        rel = piece_pts - ref["start"]
        proj = rel @ ref["direction"]
        perp = rel - np.outer(proj, ref["direction"])
        avg_dist = float(np.mean(np.linalg.norm(perp, axis=1)))
        if avg_dist > DIST_MATCH_TOLERANCE:
            continue
        if best_dist is None or avg_dist < best_dist:
            best_dist, best = avg_dist, ref
    return best


def match_curve_reference(
    piece_center: np.ndarray, piece_radius: float, curve_refs: list[dict]
) -> dict | None:
    """Find the best reference arc matching a hand-drawn curved run, if any.

    Curved counterpart to :func:`match_reference`: a radius-ratio check
    (same role as the angle check for straight runs - "is this plausibly
    the same shape") plus a center-proximity check (same role as the
    perpendicular-distance check - "is it plausibly the same ink, not a
    different nearby curve").

    Parameters
    ----------
    piece_center : np.ndarray
        The hand-drawn piece's own fitted circle center, from :func:`fit_circle`.
    piece_radius : float
        The hand-drawn piece's own fitted circle radius.
    curve_refs : list[dict]
        Candidate reference arcs, as returned by
        :func:`build_curve_reference_segments`.

    Returns
    -------
    dict | None
        The closest matching reference arc within tolerance, or ``None``
        if none match.
    """
    best, best_dist = None, None
    for ref in curve_refs:
        if ref["radius"] <= 0:
            continue
        ratio = abs(piece_radius - ref["radius"]) / ref["radius"]
        if ratio > RADIUS_MATCH_RATIO_TOLERANCE:
            continue
        center_dist = float(np.linalg.norm(piece_center - ref["center"]))
        if center_dist > CURVE_CENTER_MATCH_TOLERANCE:
            continue
        if best_dist is None or center_dist < best_dist:
            best_dist, best = center_dist, ref
    return best


def _emit_translated(segs: list, delta: np.ndarray) -> list[str]:
    """Emit path commands for segs rigidly translated by delta (no reshaping)."""
    dc = complex(delta[0], delta[1])
    parts = []
    for seg in segs:
        e = seg.end + dc
        if isinstance(seg, svgpathtools.CubicBezier):
            c1, c2 = seg.control1 + dc, seg.control2 + dc
            parts.append(
                f"C {c1.real:.1f} {c1.imag:.1f} {c2.real:.1f} {c2.imag:.1f}"
                f" {e.real:.1f} {e.imag:.1f}"
            )
        else:
            parts.append(f"L {e.real:.1f} {e.imag:.1f}")
    return parts


def refine_stroke(
    stroke_d: str,
    refs: list[dict],
    curve_refs: list[dict] | None = None,
    ref_length_match_ratio: float = 0.0,
) -> str:
    """Refine one stroke: match corner-free runs to reference segments.

    Each straight run is rigidly rotated about its (fixed) start point to the
    matched reference's exact angle - correcting the drawn angle to the
    font's actual angle. When `curve_refs` is given, each non-straight run
    that's itself close to circular is radius-corrected against its own
    best-matching reference arc instead (see "Curved runs" below). Any run
    with no good match of either kind is kept as authored (rigidly
    translated to stay attached at the corner after a neighboring
    correction).

    Curved runs
    -----------
    `curve_refs` is optional and defaults to `None`, which disables this
    entirely - every existing caller/committed cluster keeps the exact
    straight-only behavior this function always had, byte-for-byte, unless
    it explicitly opts in (`tools/process_strokes.py`'s `--curve-straighten`
    flag). When enabled: a piece is treated as "meant to be a smooth arc" if
    :func:`fit_circle` gives a low residual (`CURVE_PIECE_RESIDUAL_TOLERANCE`)
    over a long enough run (`MIN_CURVE_PIECE_LENGTH`) at a plausible radius
    (`MAX_CURVE_RADIUS`); if :func:`match_curve_reference` then finds a
    close-enough reference arc, every sampled point of the piece is pushed
    radially onto *that reference's radius* (correcting hand-drawn "wobble"
    - a radius that isn't actually constant along the stroke - while keeping
    the piece's own center as the pivot, not the reference's, since the two
    centers can differ by up to `CURVE_CENTER_MATCH_TOLERANCE` and only the
    *radius* is what the reference is more trustworthy about), re-fit as a
    smooth bezier via :func:`~jayasree.geometry.smooth_points` (reused, not
    reimplemented), then translated to attach at the running position -
    exactly the straight case's "shape corrected, position continuity kept"
    pattern, just for circles instead of lines.

    Parameters
    ----------
    stroke_d : str
        Raw SVG ``d`` string from the stroke recorder (already smoothed).
    refs : list[dict]
        Reference segments, as returned by :func:`build_reference_segments`.
    curve_refs : list[dict] | None, optional
        Reference arcs, as returned by :func:`build_curve_reference_segments`.
        `None` (the default) disables curved-run matching entirely.
    ref_length_match_ratio : float, optional
        Passed through to :func:`match_reference` as `min_length_ratio`.
        `0.0` (the default) disables the check entirely - see
        :data:`REF_LENGTH_MATCH_RATIO`'s docstring for why this is opt-in
        rather than always on.

    Returns
    -------
    str
        Refined SVG ``d`` string. Falls back to `stroke_d` unchanged if
        it's unparseable or empty.
    """
    try:
        path = svgpathtools.parse_path(stroke_d)
    except Exception:
        return stroke_d
    # A zero-length segment (its own start == end) can legitimately occur
    # in a hand-drawn or synthesized path - e.g. a tiny near-circular dot
    # stroke (Devanagari's nukta mark, or any filled-dot-shaped mark) can
    # produce one where the smoothing pass's last control point lands
    # back on the first. svgpathtools' own `derivative()` asserts
    # `self.end != self.start` and crashes outright on one, with no
    # tangent to speak of anyway - drop it before `split_path_into_pieces`
    # ever calls `derivative()` on it, rather than letting every caller of
    # this module discover the crash independently.
    path = svgpathtools.Path(*(seg for seg in path if seg.start != seg.end))
    if len(path) == 0:
        return stroke_d

    pieces = split_path_into_pieces(path)

    d_parts: list[str] = []
    running_offset = np.zeros(2)
    for segs in pieces:
        orig_start = np.array([segs[0].start.real, segs[0].start.imag])
        orig_end = np.array([segs[-1].end.real, segs[-1].end.imag])
        actual_start = orig_start + running_offset

        if not d_parts:
            d_parts.append(f"M {actual_start[0]:.1f} {actual_start[1]:.1f}")

        pts = sample_piece(segs)
        _, direction, residual, pmin, pmax = fit_line(pts)
        is_straight = (
            residual < STRAIGHT_RESIDUAL_TOLERANCE and (pmax - pmin) > MIN_STRAIGHT_PIECE_LENGTH
        )
        match = (
            match_reference(pts, direction, refs, ref_length_match_ratio)
            if (is_straight and refs)
            else None
        )

        corrected_pts = None
        if match is None and curve_refs and not is_straight:
            # A hand-drawn compound curve (e.g. a consonant's loop blending
            # into a stem) is rarely one clean circle end to end - find
            # whichever *sub-runs* of this piece are circular instead of
            # fitting one circle to the whole thing (see find_curved_segments's
            # "Dual use" docstring section). Only runs that also match a real
            # reference arc get corrected; everything else - including gaps
            # between runs - is left exactly as sampled.
            runs = find_curved_segments(
                [pts],
                tolerance=CURVE_PIECE_RESIDUAL_TOLERANCE,
                min_length=MIN_CURVE_PIECE_LENGTH,
                max_radius=MAX_CURVE_RADIUS,
            )
            matched_any = False
            working = pts.copy()
            for run in runs:
                run_pts = run["points"]
                center, radius, _ = fit_circle(run_pts)
                curve_match = match_curve_reference(center, radius, curve_refs)
                if curve_match is None:
                    continue
                matched_any = True
                offsets = run_pts - center
                norms = np.linalg.norm(offsets, axis=1, keepdims=True)
                norms[norms < 1e-9] = 1e-9
                corrected_run = center + offsets / norms * curve_match["radius"]
                # Feather the correction in/out over a few samples at each
                # end instead of splicing it in with a hard cut - a bare
                # replacement leaves a position discontinuity exactly at the
                # boundary with this run's untouched neighbors, which
                # smooth_points()'s own corner detector then reads as a real
                # corner and degenerates into a straight segment right where
                # the curve should stay smooth (confirmed empirically before
                # adding this). Blending ramps the correction from 0 (same
                # as the original point - continuous with the neighbor
                # outside the run) up to full strength in the run's middle
                # and back down, same idea as a crossfade.
                n_run = len(run_pts)
                feather = max(2, min(5, n_run // 4))
                weight = np.ones(n_run)
                # weight[0]/weight[-1] must be exactly 0 (fully the original
                # point) to match this run's untouched neighbor with zero
                # position discontinuity - a ramp that starts above 0 is
                # exactly the bug that produced the artificial corner above.
                ramp = np.linspace(0.0, 1.0, feather)
                weight[:feather] = ramp
                weight[-feather:] = ramp[::-1]
                weight = weight[:, None]
                blended_run = run_pts * (1 - weight) + corrected_run * weight
                working[run["i0"] : run["i1"] + 1] = blended_run
            if matched_any:
                corrected_pts = working

        if match is not None:
            vec = orig_end - orig_start
            ref_dir = match["direction"]
            if np.dot(vec, ref_dir) < 0:
                ref_dir = -ref_dir
            new_end = actual_start + ref_dir * np.dot(vec, ref_dir)
            d_parts.append(f"L {new_end[0]:.1f} {new_end[1]:.1f}")
            running_offset = new_end - orig_end
        elif corrected_pts is not None:
            # Shift the *points* (not the resulting path string) to attach
            # at the running position before fitting - so smooth_points()
            # already emits final, absolute coordinates and this branch
            # needs no path-string surgery, same as every other branch here.
            corrected_pts = corrected_pts + (actual_start - corrected_pts[0])
            body = smooth_points(corrected_pts)
            if body is None:
                d_parts.extend(_emit_translated(segs, running_offset))
            else:
                # smooth_points() always starts "M x y " (its own docstring);
                # that M duplicates the one this function already emitted
                # for the stroke as a whole, so drop just that leading token.
                d_parts.append(body.split(" ", 3)[3])
                running_offset = corrected_pts[-1] - orig_end
        else:
            d_parts.extend(_emit_translated(segs, running_offset))
            # running_offset unchanged: the whole piece moved by it uniformly,
            # so its end (this piece's contribution to the next start) is
            # already exactly orig_end + running_offset.

    return " ".join(d_parts)
