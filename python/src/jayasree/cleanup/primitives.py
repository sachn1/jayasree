"""Geometric primitives for stroke cleanup: dots, exact straight lines and straight runs.

A hand never draws a stem dead straight or two dots identically, but the font does. A recorded
stroke that is a dot or a line is replaced by the exact primitive, placed on the font's own ink;
a straight stretch inside a longer stroke becomes an exact line joined smoothly to the curves
around it.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from jayasree import centering
from jayasree.cleanup.fitting import fit_polyline, fit_with_tangents, line_bezier, unit
from jayasree.cleanup.ink import inside_ink, radius_fu, ridge_polyline, snap_to_ridge

#: A recorded stroke smaller than this (font units) in both axes is a dot.
DOT_MAX_EXTENT = 70.0
#: A stroke this long (font units) or longer, and straight to within hand wobble, is a line.
LINE_MIN_LEN = 120.0
#: A line within this many degrees of horizontal/vertical becomes exactly H/V. A hand never draws a
#: stem dead straight, so "nearly" has to be generous.
AXIS_SNAP_DEG = 7.0
#: Largest deviation (font units) of a stretch from its chord for it to count as a straight run.
#: Over 250 units this admits only radius > ~3900, i.e. genuinely straight stems (3-4 units starts
#: to admit bowed bars).
RUN_TOL = 2.0
#: A straight stem this long or longer is manufactured; near-flat stretches shorter than this stay
#: with the fair curve.
RUN_MIN_LEN = 120.0
#: Minimum curved stretch (font units) between two straight runs.
RUN_MIN_GAP = 120.0
#: An ink blob larger than this (font units) is part of a letter, not a dot.
ISOLATED_DOT_MAX_EXTENT = 160.0


def classify_stroke(pts: np.ndarray) -> str:
    """Return ``"dot"``, ``"line"`` or ``"curve"`` for a recorded stroke's sampled points.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` sampled points of a recorded stroke.

    Returns
    -------
    str
        The stroke's kind.
    """
    if np.ptp(pts, axis=0).max() < DOT_MAX_EXTENT:
        return "dot"
    length = np.hypot(*np.diff(pts, axis=0).T).sum()
    c = pts.mean(0)
    vt = np.linalg.svd(pts - c)[2]
    dev = np.abs((pts - c) @ vt[1]).max()
    if length >= LINE_MIN_LEN and dev < max(10.0, 0.02 * length):
        return "line"
    return "curve"


def axis_direction(v: np.ndarray, snap_deg: float = AXIS_SNAP_DEG) -> np.ndarray | None:
    """Return the exact axis direction ``(+-1, 0)`` / ``(0, +-1)`` if `v` is within `snap_deg`.

    Parameters
    ----------
    v : np.ndarray
        Direction vector ``(dx, dy)``.
    snap_deg : float
        How close to an axis (degrees) a direction must be to snap onto it.

    Returns
    -------
    np.ndarray | None
        The axis direction, or ``None`` if `v` is not close to an axis.
    """
    ang = np.degrees(np.arctan2(v[1], v[0]))
    if min(abs(ang), 180 - abs(ang)) < snap_deg:
        return np.array([np.sign(v[0]) or 1.0, 0.0])
    if abs(abs(ang) - 90) < snap_deg:
        return np.array([0.0, np.sign(v[1]) or 1.0])
    return None


def exact_line(
    a: np.ndarray, b: np.ndarray, snap_deg: float = AXIS_SNAP_DEG
) -> tuple[np.ndarray, np.ndarray]:
    """Return a -> b as an exactly straight segment (pivoted onto an axis if it is close).

    Parameters
    ----------
    a : np.ndarray
        Start point ``(x, y)``, in font units.
    b : np.ndarray
        End point ``(x, y)``, in font units.
    snap_deg : float
        How close to an axis (degrees) a direction must be to snap onto it.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        The two end points of the straightened segment.
    """
    d = axis_direction(b - a, snap_deg)
    if d is None:
        return a.copy(), b.copy()
    mid, half = (a + b) / 2, np.linalg.norm(b - a) / 2
    return mid - d * half, mid + d * half


def manufacture_dot(
    pts: np.ndarray, field: centering.DistField, search_fu: float = 60.0
) -> str | None:
    """Return one consistent dot at the centre of the font's ink blob nearest the squiggle.

    Returns ``None`` if the spot is not an isolated blob: a tiny recorded stroke inside a letter's
    own ink is a stray pen tap, not a dot, and is left for review, not drawn as a spurious spot.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` points of the recorded squiggle.
    field : centering.DistField
        The cluster's winding-aware distance field.
    search_fu : float
        How far to look for the nearest ink blob, in font units.

    Returns
    -------
    str | None
        An SVG path ``d`` for the dot, or ``None`` if the spot is not an isolated blob.
    """
    r, c = snap_to_ridge(field, pts.mean(0), search_fu)
    comp, _ = label(field.dist > 0)
    lab = comp[r, c]
    if lab == 0:
        return None
    rows, cols = np.nonzero(comp == lab)
    scale = field.w / centering.RASTER_SIZE
    if max(np.ptp(rows), np.ptp(cols)) * scale > ISOLATED_DOT_MAX_EXTENT:
        return None
    x, y = centering.px_to_fu(field, r, c)
    # 1 unit long: round caps draw the dot, and a length > 0 keeps the dash animation valid
    return f"M {x - 0.5:.1f} {y:.1f} L {x + 0.5:.1f} {y:.1f}"


def manufacture_line(
    pts: np.ndarray, field: centering.DistField, corridor_fu: float = 50.0
) -> str | None:
    """Return an exact straight line along the font's own stem centre, or ``None`` if not valid.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` points of the recorded stroke.
    field : centering.DistField
        The cluster's winding-aware distance field.
    corridor_fu : float
        Half-width of the corridor around the human's path, in font units.

    Returns
    -------
    str | None
        An SVG path ``d`` for the line, or ``None`` if it cannot be validated.
    """
    m = ridge_polyline(pts, field, 18.0, corridor_fu, 6.0)
    if len(m) < 6:
        return None
    k = max(1, int(0.1 * len(m)))
    core = m[k:-k] if len(m) > 2 * k + 3 else m
    c = core.mean(0)
    direction = np.linalg.svd(core - c)[2][0]
    if np.dot(direction, m[-1] - m[0]) < 0:
        direction = -direction
    axis = axis_direction(direction)
    if axis is not None:
        d = axis
        # position across the stem = median of the ridge (robust to a junction pulling the mean)
        n = np.array([-d[1], d[0]])
        off = np.median(core @ n)
    else:
        d = direction
        n = np.array([-d[1], d[0]])
        off = c @ n
    a = m[0] - (m[0] @ n - off) * n
    b = m[-1] - (m[-1] @ n - off) * n
    if not inside_ink(field, a, b, float(np.median(radius_fu(field, core)))):
        return None
    return f"M {a[0]:.1f} {a[1]:.1f} L {b[0]:.1f} {b[1]:.1f}"


def straight_runs(
    c: np.ndarray, tol: float = RUN_TOL, min_len: float = RUN_MIN_LEN
) -> list[tuple[int, int]]:
    """Return the maximal index runs (i, j) of the curve `c` that stay within `tol` of the chord.

    Parameters
    ----------
    c : np.ndarray
        ``(n, 2)`` curve to search.
    tol : float
        Largest deviation of a stretch from its chord, in font units.
    min_len : float
        Shortest run worth returning, in font units.

    Returns
    -------
    list[tuple[int, int]]
        ``(i, j)`` index pairs, in order.
    """
    n, runs, i = len(c), [], 0
    while i < n - 2:
        best = None
        for j in range(i + 2, n):
            v = c[j] - c[i]
            length = np.linalg.norm(v)
            if length < 1e-6:
                break
            rel = c[i : j + 1] - c[i]
            if np.abs(rel[:, 0] * v[1] - rel[:, 1] * v[0]).max() / length > tol:
                break
            best = j
        if best is not None and np.linalg.norm(c[best] - c[i]) >= min_len:
            runs.append((i, best))
            i = best
        else:
            i += 1

    # A gently bowed bar yields several short "runs" split by tiny curved gaps; the joins between
    # them are what add wiggles. Keep two runs only if real curve lies between them.
    def span(r: tuple[int, int]) -> float:
        return float(np.linalg.norm(c[r[1]] - c[r[0]]))

    kept: list[tuple[int, int]] = []
    for r in runs:
        if kept and np.linalg.norm(c[r[0]] - c[kept[-1][1]]) < RUN_MIN_GAP:
            if span(r) > span(kept[-1]):
                kept[-1] = r
            continue
        kept.append(r)
    return kept


def plan_lines(
    ridge: np.ndarray, radius: np.ndarray, field: centering.DistField
) -> list[tuple[int, int, np.ndarray, np.ndarray]]:
    """Return the straight runs of the font's own centre-line `ridge` as exact lines.

    Each is ``(i, j, a, b)``: the ridge index range and the line's end points. Straightness is
    judged on the ridge, never on the fitted curve: a minimum-bending curve is locally straight
    between its bends even on a curved letter, so runs found on it are artefacts.

    Parameters
    ----------
    ridge : np.ndarray
        ``(n, 2)`` ridge polyline (the font's own centre line), in font units.
    radius : np.ndarray
        Ink half-width at each ridge point, in font units (length ``n``).
    field : centering.DistField
        The cluster's winding-aware distance field.

    Returns
    -------
    list[tuple[int, int, np.ndarray, np.ndarray]]
        One ``(i, j, a, b)`` per run.
    """
    lines = []
    for i, j in straight_runs(ridge):
        a, b = exact_line(ridge[i], ridge[j])
        if not inside_ink(field, a, b, float(np.median(radius[i : j + 1]))):
            a, b = ridge[i].copy(), ridge[j].copy()
        lines.append((i, j, a, b))
    return lines


def line_pins(
    ridge: np.ndarray, lines: list[tuple[int, int, np.ndarray, np.ndarray]]
) -> dict[int, np.ndarray]:
    """Return the target point along each exact line, per ridge index, for the fairing step.

    Parameters
    ----------
    ridge : np.ndarray
        ``(n, 2)`` ridge polyline (the font's own centre line), in font units.
    lines : list[tuple[int, int, np.ndarray, np.ndarray]]
        Exact lines as ``(i, j, a, b)``: the ridge index range and the line's end points.

    Returns
    -------
    dict[int, np.ndarray]
        ``{ridge index: target point}``.
    """
    pins = {}
    for i, j, a, b in lines:
        for k in range(i, j + 1):
            pins[k] = a + (b - a) * ((k - i) / max(1, j - i))
    return pins


def assemble_with_lines(
    c: np.ndarray, fit_err: float, lines: list[tuple[int, int, np.ndarray, np.ndarray]]
) -> list[np.ndarray]:
    """Return Bezier segments for `c` (pinned to the lines): exact lines, G1 curves between.

    Parameters
    ----------
    c : np.ndarray
        ``(n, 2)`` faired curve, already pinned to the lines.
    fit_err : float
        Largest allowed distance from the Bezier fit to the curve, in font units.
    lines : list[tuple[int, int, np.ndarray, np.ndarray]]
        Exact lines as ``(i, j, a, b)``: the ridge index range and the line's end points.

    Returns
    -------
    list[np.ndarray]
        Cubics covering `c`, in order.
    """
    if not lines:
        return fit_polyline(c, fit_err)
    segs, cursor = [], 0
    for idx, (i, j, a, b) in enumerate(lines):
        if i - cursor >= 2:
            seg = c[cursor : i + 1].copy()
            seg[-1] = a
            t_start = None
            if cursor > 0:
                seg[0] = lines[idx - 1][3]
                t_start = unit(lines[idx - 1][3] - lines[idx - 1][2])
            segs += fit_with_tangents(seg, fit_err, t_start=t_start, t_end=unit(b - a))
        segs.append(line_bezier(a, b))
        cursor = j
    if len(c) - 1 - cursor >= 2:
        seg = c[cursor:].copy()
        seg[0] = lines[-1][3]
        segs += fit_with_tangents(seg, fit_err, t_start=unit(lines[-1][3] - lines[-1][2]))
    return segs
