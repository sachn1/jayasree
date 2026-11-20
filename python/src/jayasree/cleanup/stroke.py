"""Clean one recorded stroke: keep the human's topology, take the geometry from the font.

A recorded stroke holds two kinds of information. *Topology* - order, direction, where the corners
are - only the human can supply. *Geometry* - the exact curve through the ink - the font already
knows. So, in order of preference:

1. a dot or a straight line is replaced by the exact primitive on the font's ink;
2. otherwise the stroke follows the ink's ridge between the human's anchors (see
   :mod:`jayasree.cleanup.ink`), with the human's own path spliced back in where the ridge cannot be
   trusted (a hand-drawn curl in one thick blob of ink);
3. the ridge is faired (least bending energy) inside the ink's channel, corners the font really has
   are kept, corners the human rounded are rounded, straight stretches become exact lines and round
   ones exact circular arcs;
4. the result is a handful of cubic Beziers - an approximation, so hand tremor is not carried over.
"""

from __future__ import annotations

import itertools

import numpy as np

from jayasree import centering, geometry
from jayasree.cleanup.fitting import (
    beziers_to_d,
    line_bezier,
    smooth_pinned,
    unit,
)
from jayasree.cleanup.ink import make_field_winding, radius_fu, ridge_polyline
from jayasree.cleanup.primitives import (
    assemble_with_lines,
    classify_stroke,
    line_pins,
    manufacture_dot,
    manufacture_line,
    plan_lines,
)
from jayasree.cleanup.shape import (
    MIN_CHANNEL_FU,
    SPLICED_PIECE_SIGMA_FU,
    STEM_ROUND_FU,
    STEM_ROUND_MIN_TURN_DEG,
    band_width,
    circle_snap_fit,
    corner_fillets,
    fair_in_channel,
    font_corners,
    splice_knots,
    stem_split,
)

__all__ = ["clean_stroke", "clean_strokes"]


def _round_stem_junction(
    m: np.ndarray, radius: np.ndarray, stem: tuple, step: float
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], np.ndarray | None]:
    """Prepare the head and exact stem lines of a stroke that ends going up then down a stem.

    Returns ``(head, head_radius, stem_points, bridge)``: the head's ridge, its ink radii, the
    stem's three points ``[start, tip, end]`` and, when the head turns into the stem at an angle,
    the cubic that rounds that corner (otherwise ``None``).
    """
    head, (p_junction, p_tip, p_end), on_axis = stem
    m = head.copy()
    # If the head ends by running up alongside the stem from a corner (a crossbar turning up into
    # it), that run IS the stem: put it exactly on the stem's axis instead of letting it drift
    # across to it, which draws a slanted ramp. The stem line then starts at the corner.
    head_corners = font_corners(m, radius[: len(m)], step=step)
    corner = head_corners[-1] if head_corners else None
    if (
        corner is not None
        and corner >= 8
        and band_width(m[corner:]) < 14.0
        and float(np.linalg.norm(m[corner] - on_axis(m[corner]))) < 30.0
    ):
        m = m[: corner + 1].copy()
        m[-1] = on_axis(m[corner])
        p_junction = m[-1]
    else:
        m[-1] = p_junction
    stem_pts = [p_junction, p_tip, p_end]
    up = unit(p_tip - p_junction)
    back, run = len(m) - 1, 0.0  # walk back along the head by about STEM_ROUND_FU of path
    while back > 0 and run < STEM_ROUND_FU:
        run += float(np.linalg.norm(m[back] - m[back - 1]))
        back -= 1
    arrive = unit(m[min(back + 3, len(m) - 1)] - m[back])
    turn = float(np.degrees(np.arccos(np.clip(arrive @ up, -1.0, 1.0))))
    bridge = None
    if back >= 8 and turn > STEM_ROUND_MIN_TURN_DEG:
        # Round the corner where the head meets the stem: stop the head a little early and bridge to
        # a point up the stem with a cubic that leaves along the head's direction and arrives along
        # the stem's.
        start = m[back].copy()
        on_stem = p_junction + up * min(run, 0.5 * float(np.linalg.norm(p_tip - p_junction)))
        reach = 0.5 * float(np.linalg.norm(on_stem - start))
        bridge = np.array([start, start + arrive * reach, on_stem - up * reach, on_stem])
        m, stem_pts = m[: back + 1], [on_stem, p_tip, p_end]
    return m, radius[: len(m)], stem_pts, bridge


def clean_stroke(
    raw_d: str,
    field: centering.DistField,
    alpha: float = 0.45,
    centre_w: float = 0.02,
    fit_err: float = 5.0,
    n_samples: int = 240,
    corridor_fu: float = 70.0,
    snap_fu: float = 18.0,
    step: float = 6.0,
    centre_sigma: float = 18.0,
    jerk_w: float = 4.0,
) -> tuple[str, str]:
    """Clean one recorded stroke against the font's ink.

    Parameters
    ----------
    raw_d : str
        The recorded stroke's SVG path.
    field : centering.DistField
        The cluster's winding-aware distance field (see ``ink.make_field_winding``).
    alpha, centre_w, jerk_w : float
        The fairing channel: fraction of the ink radius, pull toward the ridge, jerk weight.
    fit_err : float
        Largest distance (font units) from the Bezier fit to the faired curve.
    n_samples : int
        Points sampled from the recorded stroke.
    corridor_fu, snap_fu : float
        Half-width of the corridor around the human's path, and how far an anchor may snap to the
        ridge (both font units).
    step, centre_sigma : float
        Resampling step and smoothing of the ridge (font units).

    Returns
    -------
    tuple[str, str]
        ``(path d, kind)``: `kind` is ``"dot"`` or ``"line"`` (manufactured), ``"curve"`` (a fair
        trace) or ``"stray_tap"`` (a recorded squiggle inside a letter's ink, kept as recorded).
    """
    pts = geometry.sample_path(raw_d, n_samples)
    kind = classify_stroke(pts)
    if kind == "dot":
        d = manufacture_dot(pts, field)
        return (d, "dot") if d is not None else (raw_d, "stray_tap")
    if kind == "line":
        d = manufacture_line(pts, field)
        if d is not None:
            return d, "line"
    m = ridge_polyline(pts, field, snap_fu, corridor_fu, step)
    radius = radius_fu(field, m)
    stem = stem_split(m, pts, radius, step)
    bridge = None
    stem_pts: list[np.ndarray] = []
    if stem is not None:  # e.g. ख: a loop that runs on into a stem drawn up then down
        m, radius, stem_pts, bridge = _round_stem_junction(m, radius, stem, step)
    m, knots = splice_knots(m, pts, radius, step=step)
    if knots:  # the splice changed the polyline: relight its joins and re-measure the radius
        m = smooth_pinned(m, 4.0, step)
        radius = radius_fu(field, m)
    corners = font_corners(m, radius, step=step)
    fillets = corner_fillets(m, corners, pts, radius, step)
    cuts = [0, *corners, len(m) - 1]
    pieces: list[list[np.ndarray]] = []
    for lo, hi in itertools.pairwise(cuts):
        # a rounded corner trims its two sides back (see corner_fillets); the bridge is added after
        keep_lo = lo + fillets[lo][0] if lo in fillets else lo
        keep_hi = hi - fillets[hi][0] if hi in fillets else hi
        if keep_hi - keep_lo < 8:
            keep_lo, keep_hi = lo, hi
        seg, rad = m[keep_lo : keep_hi + 1], radius[keep_lo : keep_hi + 1]
        # a piece holding a spliced knot keeps the human's shape - heavy smoothing would round the
        # curl away - but is still smoothed lightly, or the joins show as a bend
        spliced = any(k_lo <= hi and lo <= k_hi for k_lo, k_hi in knots)
        if len(seg) > 8:
            seg = smooth_pinned(seg, SPLICED_PIECE_SIGMA_FU if spliced else centre_sigma, step)
        grid = np.linspace(0, 1, len(seg))
        rad = np.maximum(np.interp(grid, np.linspace(0, 1, len(rad)), rad), MIN_CHANNEL_FU)
        lines = plan_lines(seg, rad, field)
        fair = fair_in_channel(seg, rad, alpha, centre_w, jerk_w, pin_points=line_pins(seg, lines))
        round_segs = None if lines else circle_snap_fit(fair, fit_err)
        pieces.append(
            round_segs if round_segs is not None else assemble_with_lines(fair, fit_err, lines)
        )
        if hi in fillets and keep_hi != hi:
            pieces.append([fillets[hi][1]])
    if stem is not None:
        p_start, p_tip, p_end = stem_pts
        bridge_segs = [bridge] if bridge is not None else []
        pieces.append([*bridge_segs, line_bezier(p_start, p_tip), line_bezier(p_tip, p_end)])
    return beziers_to_d(pieces), "curve"


def clean_strokes(raw_ds: list[str], glyphs: list[dict]) -> list[str]:
    """Clean every recorded stroke of one cluster against that cluster's own outline.

    Parameters
    ----------
    raw_ds : list[str]
        The cluster's recorded stroke paths, in drawing order.
    glyphs : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data``.

    Returns
    -------
    list[str]
        The cleaned paths, one per recorded stroke, in the same order.
    """
    field = make_field_winding(glyphs)
    return [clean_stroke(d, field)[0] for d in raw_ds]
