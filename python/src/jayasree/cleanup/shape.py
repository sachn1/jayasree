"""Shape analysis for stroke cleanup: corners, the fair curve in the ink, knots, stems and circles.

The ridge (the middle of the ink) is the right guide almost everywhere. Where it cannot be trusted
- it leaves the ink, or both passes of a hand-drawn loop collapse onto one line - the human's own
path is spliced back in. Corners the font really has are kept; corners the writer rounded are
rounded. Round stretches become exact circular arcs; a stem drawn up then down becomes two exact
lines.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.optimize import lsq_linear
from scipy.spatial import cKDTree

from jayasree.cleanup.fitting import (
    fit_with_tangents,
    line_bezier,
    resample,
    smooth_pinned,
    unit,
)
from jayasree.cleanup.ink import tangents
from jayasree.cleanup.primitives import axis_direction

#: Ridge radius (font units) below which the ridge is off, or on the edge of, the ink.
R_MIN = 10.0
#: The ridge reversing by more than this many degrees means both passes of a curl collapsed.
UTURN_DEG = 130.0
#: Font units either side of a point when measuring a reversal.
UTURN_REACH = 48.0
#: Ridge samples of context added around a bad span.
KNOT_MARGIN = 8
#: The human's path in a flagged span stays within this (font units) of one line ...
SPUR_BAND_FU = 15.0
#: ... and is this many times longer than its own chord: an out-and-back, not a curl.
SPUR_LENGTH_RATIO = 4.0
#: How far back along the head, and up the stem, the corner into a stem is rounded.
STEM_ROUND_FU = 130.0
#: A join turning less than this many degrees needs no rounding.
STEM_ROUND_MIN_TURN_DEG = 25.0
#: Most a corner is trimmed back on each side when it is rounded (font units).
FILLET_MAX_FU = 50.0
#: A corner turning less than this many degrees is already smooth.
FILLET_MIN_TURN_DEG = 30.0
#: The human's path must cut a corner by at least this (font units) for it to count as rounded.
FILLET_MIN_CUT_FU = 6.0
#: Smoothing for a piece holding a spliced-in stretch of the human's path (lighter than elsewhere).
SPLICED_PIECE_SIGMA_FU = 12.0
#: A stretch counts as circular if it stays within this (font units) of its best-fit circle ...
CIRCLE_TOL_FU = 8.0
#: ... and sweeps at least this many degrees of the circle ...
CIRCLE_MIN_DEG = 100.0
#: ... with a radius in this range (smaller is a hook, larger is nearly straight).
CIRCLE_RADIUS_FU = (25.0, 500.0)
#: Samples over which a snapped circle is blended back into the unsnapped curve.
CIRCLE_BLEND_SAMPLES = 10
#: Floor on the ink radius fed to the fairing channel (a zero-width channel is infeasible).
MIN_CHANNEL_FU = 6.0

#: A circular stretch: ``(i, j, centre, radius, signed sweep in radians)``.
CircularRun = tuple[int, int, np.ndarray, float, float]
#: A stem split: the head, the stem's three points, and the projection onto the stem's axis.
StemSplit = tuple[
    np.ndarray,
    tuple[np.ndarray, np.ndarray, np.ndarray],
    Callable[[np.ndarray], np.ndarray],
]


def font_corners(
    m: np.ndarray, radius: np.ndarray, turn_deg: float = 55.0, step: float = 6.0
) -> list[int]:
    """Return the indices where the ridge itself turns sharply (a real corner, not hand tremor)."""
    n = len(m)
    found: list[int] = []
    ang = np.zeros(n)
    for i in range(n):
        k = max(2, int((radius[i] + 10.0) / step))
        if i - k < 0 or i + k >= n:
            continue
        a, b = m[i] - m[i - k], m[i + k] - m[i]
        cosv = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        ang[i] = np.degrees(np.arccos(np.clip(cosv, -1, 1)))
    for i in range(n):
        k = max(2, int((radius[i] + 10.0) / step))
        if ang[i] > turn_deg and ang[i] == ang[max(0, i - k) : i + k + 1].max():
            if not found or i - found[-1] > 2 * k:
                found.append(i)
    return found


def fair_in_channel(
    m: np.ndarray,
    radius: np.ndarray,
    alpha: float = 0.45,
    centre_w: float = 0.02,
    jerk_w: float = 0.0,
    pin: tuple[int, ...] = (0, -1),
    pin_points: dict[int, np.ndarray] | None = None,
) -> np.ndarray:
    """Return the fairest (least bending energy) curve that stays within ``alpha * radius`` of `m`.

    Unknowns are offsets ``t_i`` along the ridge normals; ``c_i = m_i + t_i n_i``. Minimise
    ``sum |second difference of c|^2 + jerk_w * sum |third difference of c|^2`` (curvature should
    change slowly, as a hand makes it) ``+ centre_w * sum t_i^2`` subject to
    ``|t_i| <= alpha * r_i`` and ``t = 0`` at the pinned points. A bounded linear least-squares
    problem, so it is convex and has one answer - no tuning loop, no randomness.

    Parameters
    ----------
    m : np.ndarray
        ``(n, 2)`` ridge polyline.
    radius : np.ndarray
        Ink half-width at each point (font units).
    alpha, centre_w, jerk_w : float
        Channel fraction, pull toward the ridge, and the weight of the jerk term.
    pin : tuple[int, ...]
        Indices held exactly on the ridge (by default both ends).
    pin_points : dict[int, np.ndarray] | None
        Exact positions for some indices (a snapped straight run); the channel bound is ignored.

    Returns
    -------
    np.ndarray
        The faired ``(n, 2)`` polyline.
    """
    n = len(m)
    if n < 5:
        return m
    nrm = tangents(m) @ np.array([[0, 1], [-1, 0]])
    second = np.zeros((n - 2, n))
    for i in range(n - 2):
        second[i, i], second[i, i + 1], second[i, i + 2] = 1, -2, 1
    blocks_a = [second * nrm[:, 0], second * nrm[:, 1], np.sqrt(centre_w) * np.eye(n)]
    blocks_b = [second @ m[:, 0], second @ m[:, 1], np.zeros(n)]
    if jerk_w > 0 and n >= 6:
        third = np.zeros((n - 3, n))
        for i in range(n - 3):
            third[i, i], third[i, i + 1], third[i, i + 2], third[i, i + 3] = -1, 3, -3, 1
        w = np.sqrt(jerk_w)
        blocks_a += [w * third * nrm[:, 0], w * third * nrm[:, 1]]
        blocks_b += [w * third @ m[:, 0], w * third @ m[:, 1]]
    design = np.vstack(blocks_a)
    target = -np.concatenate(blocks_b)
    ub = alpha * radius
    lb, ub = -ub, ub.copy()
    for p in pin:
        lb[p] = -1e-6
        ub[p] = 1e-6
    for k, pt in (pin_points or {}).items():
        tk = float((np.asarray(pt) - m[k]) @ nrm[k])
        lb[k], ub[k] = tk - 1e-6, tk + 1e-6
    t = lsq_linear(design, target, bounds=(lb, ub), method="bvls").x
    return m + t[:, None] * nrm


def bad_spans(m: np.ndarray, radius: np.ndarray, step: float = 6.0) -> list[tuple[int, int]]:
    """Return the index ranges of the ridge `m` that cannot be right: off the ink, or doubled back.

    The ridge is the middle of the ink. Where a hand-drawn loop (the tail curl of इ/ई) sits in one
    thick blob of ink, both passes of the loop share a single middle line, so the ridge collapses
    the loop into a cusp and cuts across the font's counter (radius ~0). Those spans must not be
    trusted.
    """
    n = len(m)
    k = max(2, int(UTURN_REACH / step))
    bad = radius < R_MIN
    for i in range(k, n - k):
        a, b = m[i] - m[i - k], m[i + k] - m[i]
        cosv = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        if np.degrees(np.arccos(np.clip(cosv, -1, 1))) > UTURN_DEG:
            bad[max(0, i - k) : i + k + 1] = True
    spans: list[list[int]] = []
    for i in np.nonzero(bad)[0]:
        lo, hi = max(0, i - KNOT_MARGIN), min(n - 1, i + KNOT_MARGIN)
        if spans and lo <= spans[-1][1] + 1:
            spans[-1][1] = max(spans[-1][1], hi)
        else:
            spans.append([lo, hi])
    return [(lo, hi) for lo, hi in spans if hi - lo >= 4]


def band_width(p: np.ndarray) -> float:
    """Return the largest distance (font units) of any point of `p` from its own best-fit line."""
    c = p - p.mean(0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    return float(np.abs(c @ vt[1]).max())


def human_index(m: np.ndarray, pts: np.ndarray, i: int, window: float = 0.2) -> int:
    """Return the index into the human's recording `pts` that matches ridge point ``m[i]``.

    The nearest recorded point is the right answer except where the stroke passes close to *itself*
    (a spiral's tail crossing its own loop): then the nearest point can be on the other pass and a
    span comes out backwards. So the search is limited to the stretch of the recording where that
    ridge point is expected, found from how far along the ridge it is.
    """
    expected = round(i / max(1, len(m) - 1) * (len(pts) - 1))
    reach = max(6, int(window * len(pts)))
    lo, hi = max(0, expected - reach), min(len(pts), expected + reach + 1)
    return lo + int(np.argmin(np.linalg.norm(pts[lo:hi] - m[i], axis=1)))


def is_spur(span_pts: np.ndarray) -> bool:
    """Return True if the human's path over a flagged span goes out and back along one line.

    That is a stem drawn up then down. Such a span is much longer than its own chord (it returns to
    where it started) yet stays within hand-wobble of a single line. A curl is wider; a span where
    the ridge merely crossed a counter is not longer than its chord.
    """
    span_len = float(np.hypot(*np.diff(span_pts, axis=0).T).sum())
    chord = float(np.linalg.norm(span_pts[-1] - span_pts[0]))
    return span_len > SPUR_LENGTH_RATIO * chord and band_width(span_pts) < SPUR_BAND_FU


def find_spurs(
    m: np.ndarray, pts: np.ndarray, radius: np.ndarray, step: float = 6.0
) -> list[tuple[int, int]]:
    """Return the ridge index ranges where the stroke goes up a stem and back down it."""
    out = []
    for lo, hi in bad_spans(m, radius, step):
        j0, j1 = human_index(m, pts, lo), human_index(m, pts, hi)
        if j1 - j0 >= 3 and is_spur(pts[j0 : j1 + 1]):
            out.append((lo, hi))
    return out


def stem_split(
    m: np.ndarray, pts: np.ndarray, radius: np.ndarray, step: float = 6.0
) -> StemSplit | None:
    """Split a stroke that ends by going up a straight stem and back down it.

    Returns ``(head, (p_junction, p_tip, p_end), proj)`` with the three stem points on one exact
    line (snapped to the vertical/horizontal when close) and ``proj``, the projection of any point
    onto that line - or ``None`` when the stroke has no such stem. The head is the part of the
    ridge before the stem is first reached; the caller rebuilds the stem as two exact straight
    segments.
    """
    spurs = find_spurs(m, pts, radius, step)
    if len(spurs) != 1:
        return None
    a, b = spurs[0]
    if a < 8 or len(m) - b < 12:
        return None
    tip = a + int(np.argmax(np.linalg.norm(m[a : b + 1] - m[a], axis=1)))
    stem = np.vstack([m[tip], m[b:]])
    if np.linalg.norm(m[tip] - m[-1]) < 120.0 or band_width(stem) >= 16.0:
        return None
    c = stem.mean(0)
    direction = np.linalg.svd(stem - c, full_matrices=False)[2][0]
    snapped = axis_direction(direction)
    d = snapped if snapped is not None else direction

    def proj(q: np.ndarray) -> np.ndarray:
        """Project `q` onto the stem axis."""
        return c + d * float((q - c) @ d)

    return m[: a + 1], (proj(m[a]), proj(m[tip]), proj(m[-1])), proj


def corner_fillets(
    m: np.ndarray, corners: list[int], pts: np.ndarray, radius: np.ndarray, step: float = 6.0
) -> dict[int, tuple[int, np.ndarray]]:
    """Return how to round each sharp ridge corner that the human rounded.

    The ridge is the middle of the ink, so where a thin band meets another at an angle (a crossbar
    running into a stem) it turns sharply - but a hand draws that as a curve. A corner is rounded
    only when the recorded path really cut it (it passes at least ``FILLET_MIN_CUT_FU`` from the
    corner point), so a corner the writer kept sharp stays sharp. How much it is rounded is the
    larger of what the hand cut and 0.8 of the ink's half-width there (a pen as wide as the stroke
    cannot turn tighter than that), capped at ``FILLET_MAX_FU``.

    Returns
    -------
    dict[int, tuple[int, np.ndarray]]
        ``{corner_index: (trim_samples, bezier)}``: each side of the corner is trimmed back by
        ``trim_samples`` and the 4-point cubic bridges the gap, leaving and arriving tangent to
        the sides.
    """
    tree = cKDTree(pts)
    k = 4
    out = {}
    for c in corners:
        if c - k < 0 or c + k >= len(m):
            continue
        t_in, t_out = unit(m[c] - m[c - k]), unit(m[c + k] - m[c])
        turn = float(np.degrees(np.arccos(np.clip(t_in @ t_out, -1.0, 1.0))))
        cut = float(tree.query(m[c])[0])
        if turn < FILLET_MIN_TURN_DEG or cut < FILLET_MIN_CUT_FU:
            continue
        # a circular fillet of trim d on a right angle passes about 0.41*d from the corner:
        # invert that
        trim = round(min(max(2.4 * cut, 0.8 * float(radius[c])), FILLET_MAX_FU) / step)
        if trim < 2 or c - trim < 0 or c + trim >= len(m):
            continue
        p0, p3 = m[c - trim], m[c + trim]
        h0, h3 = 0.55 * float(np.linalg.norm(m[c] - p0)), 0.55 * float(np.linalg.norm(p3 - m[c]))
        out[c] = (trim, np.array([p0, p0 + t_in * h0, p3 - t_out * h3, p3]))
    return out


# -- exact circles for round stretches -----------------------------------------------------------
def fit_circle(p: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Return the best-fit circle of `p` (Kasa): ``(centre, radius, max deviation)``."""
    a = np.c_[2 * p[:, 0], 2 * p[:, 1], np.ones(len(p))]
    b = (p**2).sum(axis=1)
    cx, cy, k = np.linalg.lstsq(a, b, rcond=None)[0]
    centre = np.array([cx, cy])
    radius = float(np.sqrt(max(k + cx * cx + cy * cy, 1e-9)))
    return centre, radius, float(np.abs(np.linalg.norm(p - centre, axis=1) - radius).max())


def _longest_circular_run(q: np.ndarray, lo: int, hi: int) -> CircularRun | None:
    """Return the longest stretch of ``q[lo:hi]`` that is a circle to within ``CIRCLE_TOL_FU``.

    A stretch must sweep at least ``CIRCLE_MIN_DEG`` and have a radius in ``CIRCLE_RADIUS_FU``.
    Returns ``None`` if there is none.
    """
    best = None
    for i in range(lo, hi - 12, 3):
        j = i + 12
        fit = None
        while j < hi:
            centre, radius, deviation = fit_circle(q[i : j + 1])
            if deviation > CIRCLE_TOL_FU or not CIRCLE_RADIUS_FU[0] < radius < CIRCLE_RADIUS_FU[1]:
                break
            fit = (j, centre, radius)
            j += 1
        if fit is None:
            continue
        j, centre, radius = fit
        angles = np.unwrap(np.arctan2(q[i : j + 1, 1] - centre[1], q[i : j + 1, 0] - centre[0]))
        sweep = float(angles[-1] - angles[0])
        if abs(np.degrees(sweep)) >= CIRCLE_MIN_DEG and (best is None or abs(sweep) > abs(best[4])):
            best = (i, j, centre, radius, sweep)
    return best


def circular_runs(q: np.ndarray) -> list[CircularRun]:
    """Return every circular stretch of `q`: the longest first, then the longest of what is left."""
    runs: list[CircularRun] = []
    pending = [(0, len(q))]
    while pending:
        lo, hi = pending.pop()
        found = _longest_circular_run(q, lo, hi)
        if found is not None:
            runs.append(found)
            pending += [(lo, found[0]), (found[1] + 1, hi)]
    return sorted(runs, key=lambda r: r[0])


def arc_beziers(centre: np.ndarray, radius: float, angle0: float, sweep: float) -> list[np.ndarray]:
    """Return an exact circular arc as cubic Beziers (none spanning more than 90 degrees)."""
    parts = max(1, int(np.ceil(abs(sweep) / (np.pi / 2))))
    step = sweep / parts
    k = 4.0 / 3.0 * np.tan(abs(step) / 4.0)  # handle length, as a fraction of the radius
    heading = np.sign(step)  # +1 = counter-clockwise in the maths frame, -1 = clockwise
    out = []
    for s in range(parts):
        a, b = angle0 + s * step, angle0 + (s + 1) * step
        p0 = centre + radius * np.array([np.cos(a), np.sin(a)])
        p3 = centre + radius * np.array([np.cos(b), np.sin(b)])
        t0 = heading * np.array([-np.sin(a), np.cos(a)])  # unit direction of travel at each end
        t3 = heading * np.array([-np.sin(b), np.cos(b)])
        out.append(np.array([p0, p0 + t0 * k * radius, p3 - t3 * k * radius, p3]))
    return out


def circle_snap_fit(q: np.ndarray, fit_err: float) -> list[np.ndarray] | None:
    """Fit `q` with exact circular arcs where it is round, ordinary fitted curves elsewhere.

    Returns a list of Bezier segments, or ``None`` if `q` has no circular stretch (the caller then
    fits it the ordinary way). Each snapped stretch is replaced by an exact arc; its ends are
    blended back into the neighbouring curve over ``CIRCLE_BLEND_SAMPLES`` samples so the joins
    stay smooth and tangent-continuous.
    """
    f = CIRCLE_BLEND_SAMPLES
    snapped = q.copy()
    arcs_at: list[tuple[int, int, list[np.ndarray], np.ndarray, np.ndarray]] = []
    for i, j, centre, radius, sweep in circular_runs(q):
        a, b = i + f, j - f  # the fully snapped part: every point on the circle
        if b - a < 8:
            continue
        for k in range(i, j + 1):
            w = min(1.0, (k - i) / f, (j - k) / f)
            on_circle = centre + radius * (q[k] - centre) / max(np.linalg.norm(q[k] - centre), 1e-9)
            snapped[k] = q[k] + w * (on_circle - q[k])
        angles = np.unwrap(np.arctan2(q[:, 1] - centre[1], q[:, 0] - centre[0]))
        a0, a1 = angles[a], angles[b]
        direction = 1.0 if sweep > 0 else -1.0
        arcs = arc_beziers(centre, radius, a0, a1 - a0)
        t_in = np.array([-np.sin(a0), np.cos(a0)]) * direction
        t_out = np.array([-np.sin(a1), np.cos(a1)]) * direction
        arcs_at.append((a, b, arcs, t_in, t_out))
    if not arcs_at:
        return None
    segs: list[np.ndarray] = []
    cursor, prev_end, prev_tangent = 0, None, None
    for a, b, arcs, t_in, t_out in arcs_at:
        if a - cursor >= 2:
            part = snapped[cursor : a + 1].copy()
            part[-1] = arcs[0][0]
            if prev_end is not None:
                part[0] = prev_end
            segs += fit_with_tangents(part, fit_err, t_start=prev_tangent, t_end=-t_in)
        elif prev_end is not None and np.linalg.norm(arcs[0][0] - prev_end) > 0.5:
            segs.append(line_bezier(prev_end, arcs[0][0]))
        segs += arcs
        cursor, prev_end, prev_tangent = b, arcs[-1][3], t_out
    if len(q) - 1 - cursor >= 2:
        part = snapped[cursor:].copy()
        part[0] = prev_end
        segs += fit_with_tangents(part, fit_err, t_start=prev_tangent)
    return segs


def splice_knots(
    m: np.ndarray,
    pts: np.ndarray,
    radius: np.ndarray,
    sigma: float = 9.0,
    step: float = 6.0,
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Replace each untrustworthy span of the ridge with the human's own (lightly smoothed) path.

    Returns the new polyline and the index ranges *in that new polyline* that now hold the human's
    path (those must not be re-smoothed away). A span whose ends map to the same stretch of the
    recording (the ridge walked out and back along a stem) is left alone - there is no curl of the
    human's to restore.
    """
    spans = bad_spans(m, radius, step)
    if not spans:
        return m, []
    out, pos, used, n_out = [], 0, [], 0
    for lo, hi in spans:
        j0, j1 = human_index(m, pts, lo), human_index(m, pts, hi)
        if j1 - j0 < 3:
            continue
        raw_span = pts[j0 : j1 + 1]
        # Out and back along one line (a stem drawn up then down): the ridge spur there is harmless
        # and the fairing flattens it; the human's own path would only bring its wobble back.
        if is_spur(raw_span):
            continue
        human = smooth_pinned(resample(raw_span, step), sigma, step)
        keep = m[pos:lo]
        out += [keep, human]
        used.append((n_out + len(keep), n_out + len(keep) + len(human) - 1))
        n_out += len(keep) + len(human)
        pos = hi + 1
    out.append(m[pos:])
    return np.vstack(out), used
