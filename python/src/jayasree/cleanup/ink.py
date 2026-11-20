"""The font's ink as a guide: a winding-aware distance field, ridge routing and ridge measurements.

A recorded stroke says *where* a stroke goes (order, direction, corners); the font already knows the
exact curve through the ink. This module finds that curve: a minimum-cost path through the ink's
distance field (cost ~ 1 / depth^2, plus a weak pull toward the human's own path inside a corridor),
which rides the ink's ridge and, being pinned to the human's anchors, cannot jump to another branch.
"""

from __future__ import annotations

import heapq
import itertools
import math
import re

import numpy as np
import svgpathtools
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from jayasree import centering, geometry
from jayasree.cleanup.fitting import smooth_pinned

#: Cost of a cell the path must not use (outside the ink or the corridor); high, not infinite, so a
#: path between two anchors always exists.
BLOCKED_COST = 1e4
#: Corner angle (degrees) used to pick the human's corners, as routing hints only.
_RDP_EPS = 20.0

_NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def make_field_winding(glyphs: list[dict], isotropic: bool = True) -> centering.DistField:
    """Return a distance field like :func:`centering.make_dist_field` but honouring counters.

    Ink is *nonzero winding*, so a glyph's holes (counters) stay empty.
    ``make_dist_field`` fills every sub-path independently, so a counter reads as solid ink and a
    gradient ascent drifts toward its middle.

    Parameters
    ----------
    glyphs : list[dict]
        The cluster's glyph entries (``d``, ``x``, ``y``) from ``glyph-data``.
    isotropic : bool
        Pad the bounding box to a square. ``make_dist_field`` maps a w x h box onto a square raster,
        so for a wide glyph a pixel covers more font units in x than in y and the distance
        transform (which assumes square pixels) is stretched.

    Returns
    -------
    centering.DistField
        The field, in the same structure ``centering`` uses.

    Raises
    ------
    ValueError
        If the glyphs have no ink (``centering.make_dist_field`` returns an empty field instead;
        here the caller is expected to fall back to the ordinary stages).
    """
    polys = []
    for comp in glyphs:
        dx, dy = comp.get("x", 0), comp.get("y", 0)
        for sub_d in re.findall(r"M[^M]*", comp["d"]):
            try:
                sub = svgpathtools.parse_path(sub_d)
            except Exception:  # a malformed sub-path contributes no ink, as in centering
                continue
            length = sub.length()
            if length <= 0:
                continue
            n = max(64, int(length / 4))
            polys.append(
                [(sub.point(i / n).real + dx, sub.point(i / n).imag + dy) for i in range(n + 1)]
            )
    if not polys:
        raise ValueError("the glyphs have no ink to build a distance field from")
    all_pts = np.array([p for poly in polys for p in poly])
    x_min, y_min = all_pts.min(0) - centering.BBOX_PAD
    x_max, y_max = all_pts.max(0) + centering.BBOX_PAD
    if isotropic:
        side = max(x_max - x_min, y_max - y_min)
        cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
        x_min, x_max = cx - side / 2, cx + side / 2
        y_min, y_max = cy - side / 2, cy + side / 2
    w, h, size = x_max - x_min, y_max - y_min, centering.RASTER_SIZE
    wind = np.zeros((size, size), dtype=np.int16)
    for poly in polys:
        px = [((x - x_min) / w * size, (y_max - y) / h * size) for x, y in poly]
        if len(px) < 3:
            continue
        a = np.array(px)
        area = 0.5 * np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1])
        img = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img).polygon(px, fill=1)
        wind += np.array(img, dtype=np.int16) * (1 if area > 0 else -1)
    dist = distance_transform_edt(wind != 0).astype(float)
    grad_r, grad_c = np.gradient(dist)
    rows, cols = np.nonzero(dist > 0)
    tree = cKDTree(np.column_stack([rows, cols])) if len(rows) else None
    return centering.DistField(dist, grad_r, grad_c, x_min, y_min, x_max, y_max, tree)


def anchors_for(pts: np.ndarray, rdp_eps: float = _RDP_EPS) -> list[int]:
    """Return the indices into `pts` of the start, every genuine corner, and the end.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` points of the human's recorded stroke, in font units.
    rdp_eps : float
        Tolerance, in font units, of the simplification that finds the human's corners.

    Returns
    -------
    list[int]
        Indices into `pts`, in order.
    """
    idx = geometry._rdp_indices(pts, rdp_eps)
    way = pts[idx]
    corners = geometry.find_corner_indices(way) if len(way) >= 3 else []
    return [0, *[idx[c] for c in corners], len(pts) - 1]


def snap_to_ridge(field: centering.DistField, p: np.ndarray, radius_fu: float) -> tuple[int, int]:
    """Return the pixel of the deepest ink within `radius_fu` of font-unit point `p`.

    Parameters
    ----------
    field : centering.DistField
        The cluster's winding-aware distance field.
    p : np.ndarray
        Point ``(x, y)`` in font units.
    radius_fu : float
        How far to look for the deepest ink, in font units.

    Returns
    -------
    tuple[int, int]
        ``(row, col)`` of the snapped pixel.
    """
    raster = centering.RASTER_SIZE
    r0, c0 = centering.fu_to_px(field, *p)
    rad = max(2, int(radius_fu / (max(field.w, field.h) / raster)))
    r_lo, c_lo = max(0, int(r0) - rad), max(0, int(c0) - rad)
    win = field.dist[r_lo : int(r0) + rad + 1, c_lo : int(c0) + rad + 1]
    if win.size == 0 or win.max() <= 0:
        return int(np.clip(r0, 0, raster - 1)), int(np.clip(c0, 0, raster - 1))
    # prefer depth, but tie-break toward the original position
    rr, cc = np.mgrid[0 : win.shape[0], 0 : win.shape[1]]
    d2 = (rr + r_lo - r0) ** 2 + (cc + c_lo - c0) ** 2
    score = win - 0.02 * np.sqrt(d2)
    i = np.unravel_index(np.argmax(score), win.shape)
    return int(i[0] + r_lo), int(i[1] + c_lo)


def min_cost_path(
    cost: np.ndarray, start: tuple[int, int], end: tuple[int, int]
) -> list[tuple[int, int]]:
    """Return the cheapest 8-connected path from `start` to `end` over the cost grid `cost`.

    A step costs the mean of its two cells times its length (1, or the square root of 2 on a
    diagonal) - the same model as scikit-image's ``route_through_array(..., geometric=True)``,
    which this replaces to avoid a heavy dependency for one function. Only the part of the grid
    that is not blocked is searched: a path through a blocked cell costs at least
    ``BLOCKED_COST``, far more than any path that avoids them.

    Parameters
    ----------
    cost : np.ndarray
        ``(rows, cols)`` cost per cell.
    start, end : tuple[int, int]
        ``(row, col)`` of the two ends.

    Returns
    -------
    list[tuple[int, int]]
        ``(row, col)`` cells from `start` to `end`, inclusive.

    Raises
    ------
    ValueError
        If every cell is blocked. `start` and `end` must lie inside the grid (callers snap and
        clip them first); blocked cells are costly but passable, so a path always exists then.
    """
    free = np.argwhere(cost < BLOCKED_COST)
    if free.size == 0:
        raise ValueError("every cell is blocked; there is no path to find")
    corners = np.array([start, end, *free.min(0, keepdims=True), *free.max(0, keepdims=True)])
    r_lo, c_lo = np.maximum(corners.min(0) - 1, 0)
    r_hi, c_hi = corners.max(0) + 2
    grid = cost[r_lo:r_hi, c_lo:c_hi].tolist()
    rows, cols = len(grid), len(grid[0])
    src = (int(start[0]) - int(r_lo), int(start[1]) - int(c_lo))
    dst = (int(end[0]) - int(r_lo), int(end[1]) - int(c_lo))
    best = {src: 0.0}
    prev: dict[tuple[int, int], tuple[int, int]] = {}
    heap = [(0.0, src)]
    done: set[tuple[int, int]] = set()
    while heap:
        d, node = heapq.heappop(heap)
        if node in done:
            continue
        if node == dst:
            break
        done.add(node)
        r, c = node
        here = grid[r][c]
        for dr, dc in _NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols) or (nr, nc) in done:
                continue
            step = math.sqrt(2.0) if dr and dc else 1.0
            nd = d + 0.5 * (here + grid[nr][nc]) * step
            if nd < best.get((nr, nc), math.inf):
                best[(nr, nc)] = nd
                prev[(nr, nc)] = node
                heapq.heappush(heap, (nd, (nr, nc)))
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return [(r + int(r_lo), c + int(c_lo)) for r, c in reversed(path)]


def ridge_path(
    field: centering.DistField,
    a_px: tuple[int, int],
    b_px: tuple[int, int],
    human_px: list[tuple[float, float]],
    corridor_fu: float = 70.0,
    depth_pow: float = 2.0,
    prior: float = 0.15,
) -> np.ndarray:
    """Return the min-cost pixel path a -> b through the ink, near the human's own path.

    Parameters
    ----------
    field : centering.DistField
        The glyph's distance field.
    a_px, b_px : tuple[int, int]
        Start and end pixels (already snapped to the ridge).
    human_px : list[tuple[float, float]]
        The human's recorded points between the two, in pixels (the corridor's centre line).
    corridor_fu : float
        Half-width of the corridor around the human's path, in font units.
    depth_pow : float
        Exponent of the depth term: higher hugs the ridge harder.
    prior : float
        Weight of the pull toward the human's path inside the corridor.

    Returns
    -------
    np.ndarray
        ``(n, 2)`` ``(row, col)`` pixels from a to b.
    """
    size = centering.RASTER_SIZE
    scale = max(field.w, field.h) / size
    corridor_px = corridor_fu / scale
    guide = np.ones((size, size), dtype=bool)
    for (r0, c0), (r1, c1) in itertools.pairwise(human_px):
        for t in np.linspace(0, 1, max(2, int(np.hypot(r1 - r0, c1 - c0)) + 1)):
            guide[round(r0 + (r1 - r0) * t), round(c0 + (c1 - c0) * t)] = False
    d_h = distance_transform_edt(guide)
    cost = 1.0 / (field.dist + 0.5) ** depth_pow + prior * (d_h / corridor_px) ** 2
    cost[field.dist <= 0] = BLOCKED_COST
    cost[d_h > corridor_px] = BLOCKED_COST
    return np.array(min_cost_path(cost, a_px, b_px), dtype=float)


def routing_waypoints(
    pts: np.ndarray, lo: int, hi: int, max_ratio: float = 1.4, depth: int = 0
) -> list[int]:
    """Return the indices lo..hi, split wherever the human path is much longer than its chord.

    A min-cost path between two anchors takes the shortest way, so if the human drew a loop that
    returns near its start, the loop would be skipped. Splitting at the point farthest from the
    chord forces the route through it. These are routing hints only - they never become corners.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` points of the human's recorded stroke, in font units.
    lo : int
        Index of the first point of the stretch.
    hi : int
        Index of the last point of the stretch.
    max_ratio : float
        A stretch is split when its path is more than this many times its chord.
    depth : int
        Recursion depth (internal).

    Returns
    -------
    list[int]
        Indices into `pts` that the route must pass through.
    """
    seg = pts[lo : hi + 1]
    length = np.hypot(*np.diff(seg, axis=0).T).sum()
    chord = np.linalg.norm(pts[hi] - pts[lo])
    if hi - lo < 6 or depth > 6 or length <= max_ratio * max(chord, 1.0):
        return [lo, hi]
    v = pts[hi] - pts[lo]
    n = np.linalg.norm(v)
    rel = seg - pts[lo]
    if n > 1e-6:
        off = np.abs(rel[:, 0] * v[1] - rel[:, 1] * v[0]) / n
    else:
        off = np.linalg.norm(rel, axis=1)
    m = lo + int(np.argmax(off))
    m = min(max(m, lo + 2), hi - 2)
    first = routing_waypoints(pts, lo, m, max_ratio, depth + 1)[:-1]
    return first + routing_waypoints(pts, m, hi, max_ratio, depth + 1)


def ridge_polyline(
    pts: np.ndarray,
    field: centering.DistField,
    snap_fu: float,
    corridor_fu: float,
    step: float,
) -> np.ndarray:
    """Return the min-cost ridge path of a whole human stroke, as ``(n, 2)`` font units.

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` points of the human's recorded stroke, in font units.
    field : centering.DistField
        The cluster's winding-aware distance field.
    snap_fu : float
        How far an anchor may snap to the ridge, in font units.
    corridor_fu : float
        Half-width of the corridor around the human's path, in font units.
    step : float
        Resampling step along the path, in font units.

    Returns
    -------
    np.ndarray
        The smoothed ridge path, in font units.
    """
    a_idx = anchors_for(pts)  # start, end and the human's corners - routing hints ONLY
    human_px = [centering.fu_to_px(field, *p) for p in pts]
    marks = sorted(set(a_idx))
    parts = []
    for k in range(len(marks) - 1):
        route = routing_waypoints(pts, marks[k], marks[k + 1])
        first_piece, last_piece = k == 0, k == len(marks) - 2
        snapped = [
            snap_to_ridge(
                field,
                pts[i],
                snap_fu
                * (
                    0.5 if (first_piece and j == 0) or (last_piece and j == len(route) - 1) else 1.0
                ),
            )
            for j, i in enumerate(route)
        ]
        for j in range(len(route) - 1):
            px = ridge_path(
                field,
                snapped[j],
                snapped[j + 1],
                human_px[route[j] : route[j + 1] + 1],
                corridor_fu,
            )
            parts.append(np.array([centering.px_to_fu(field, r, c) for r, c in px]))
    fu = np.vstack([parts[0], *[q[1:] for q in parts[1:]]])
    return smooth_pinned(fu, 6.0, step)


def tangents(m: np.ndarray) -> np.ndarray:
    """Return the unit tangent at each point of the polyline `m`.

    Parameters
    ----------
    m : np.ndarray
        ``(n, 2)`` polyline.

    Returns
    -------
    np.ndarray
        ``(n, 2)`` unit tangents.
    """
    t = np.gradient(m, axis=0)
    n = np.linalg.norm(t, axis=1, keepdims=True)
    return t / np.maximum(n, 1e-9)


def _depth_at(field: centering.DistField, x: float, y: float) -> float:
    """Return the distance-field value (pixels of ink depth) at font-unit point (x, y)."""
    r, c = centering.fu_to_px(field, x, y)
    last = centering.RASTER_SIZE - 1
    return float(field.dist[int(np.clip(r, 0, last)), int(np.clip(c, 0, last))])


def radius_fu(field: centering.DistField, m: np.ndarray) -> np.ndarray:
    """Return the local half-width of the ink at each point of `m`, in font units.

    Parameters
    ----------
    field : centering.DistField
        The cluster's winding-aware distance field.
    m : np.ndarray
        ``(n, 2)`` ridge polyline (the middle of the ink), in font units.

    Returns
    -------
    np.ndarray
        ``(n,)`` half-widths, in font units.
    """
    scale = field.w / centering.RASTER_SIZE
    return np.array([_depth_at(field, x, y) * scale for x, y in m])


def inside_ink(
    field: centering.DistField,
    a: np.ndarray,
    b: np.ndarray,
    radius: float,
    frac: float = 0.3,
    n: int = 30,
) -> bool:
    """Return True if the segment a -> b stays deeper than ``frac * radius`` inside the ink.

    Parameters
    ----------
    field : centering.DistField
        The cluster's winding-aware distance field.
    a : np.ndarray
        Start point ``(x, y)``, in font units.
    b : np.ndarray
        End point ``(x, y)``, in font units.
    radius : float
        Ink half-width of the stretch, in font units.
    frac : float
        Fraction of `radius` the segment must stay deeper than.
    n : int
        Number of points checked along the segment.

    Returns
    -------
    bool
        Whether the whole segment stays inside the ink.
    """
    scale = field.w / centering.RASTER_SIZE
    need = frac * radius / scale
    for t in np.linspace(0, 1, n):
        x, y = a + (b - a) * t
        if _depth_at(field, x, y) < need:
            return False
    return True
