"""Curve fitting for stroke cleanup: resampling, pinned smoothing and Schneider cubic Bezier fits.

A recorded stroke is reduced to a few exact cubic Beziers. The fit is an *approximation*
(least squares), not the interpolation :func:`jayasree.geometry.fit_piece` does, so hand tremor
between the control points is not carried into the result.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d

#: A direction vector shorter than this is left as it is rather than divided by.
_EPS = 1e-9


def unit(v: np.ndarray) -> np.ndarray:
    """Return `v` scaled to length 1 (unchanged if it is effectively zero).

    Parameters
    ----------
    v : np.ndarray
        Vector to normalise.

    Returns
    -------
    np.ndarray
        The unit vector.
    """
    n = np.linalg.norm(v)
    return v / n if n > _EPS else v


def resample(pts: np.ndarray, step: float) -> np.ndarray:
    """Resample the polyline `pts` at equal arc-length spacing of about `step` (min. 4 points).

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` polyline to resample.
    step : float
        Resampling step along the path, in font units.

    Returns
    -------
    np.ndarray
        The resampled ``(n, 2)`` polyline.
    """
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.r_[0, np.cumsum(seg)]
    n = max(4, int(s[-1] / step) + 1)
    t = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])])


def smooth_pinned(pts: np.ndarray, sigma_fu: float, step: float = 4.0) -> np.ndarray:
    """Gaussian-smooth `pts` along arc length with both ends pinned (odd reflection).

    Parameters
    ----------
    pts : np.ndarray
        ``(n, 2)`` polyline to smooth.
    sigma_fu : float
        Gaussian smoothing width, in font units (0 disables smoothing).
    step : float
        Resampling step along the path, in font units.

    Returns
    -------
    np.ndarray
        The smoothed ``(n, 2)`` polyline, ends unchanged.
    """
    p = resample(pts, step)
    if sigma_fu <= 0 or len(p) < 6:
        return p
    pad = min(len(p) - 1, int(4 * sigma_fu / step))
    head = 2 * p[0] - p[1 : pad + 1][::-1]
    tail = 2 * p[-1] - p[-pad - 1 : -1][::-1]
    ext = np.vstack([head, p, tail])
    out = gaussian_filter1d(ext, sigma_fu / step, axis=0, mode="nearest")
    return out[pad : pad + len(p)]


# -- Schneider (Graphics Gems) least-squares cubic fit -------------------------------------------
def _bez(c: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Points of the cubic with control points `c` at parameters `t`."""
    t = np.asarray(t)[:, None]
    m = 1 - t
    return m**3 * c[0] + 3 * m**2 * t * c[1] + 3 * m * t**2 * c[2] + t**3 * c[3]


def _bez_d1(c: np.ndarray, t: np.ndarray) -> np.ndarray:
    """First derivative of the cubic `c` at `t`."""
    t = np.asarray(t)[:, None]
    m = 1 - t
    return 3 * m**2 * (c[1] - c[0]) + 6 * m * t * (c[2] - c[1]) + 3 * t**2 * (c[3] - c[2])


def _bez_d2(c: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Second derivative of the cubic `c` at `t`."""
    t = np.asarray(t)[:, None]
    return 6 * (1 - t) * (c[2] - 2 * c[1] + c[0]) + 6 * t * (c[3] - 2 * c[2] + c[1])


def _chord_param(p: np.ndarray) -> np.ndarray:
    """Chord-length parameter in [0, 1] for each point of `p`."""
    u = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    return u / u[-1]


def _generate(p: np.ndarray, u: np.ndarray, t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
    """Least-squares cubic through `p` (parameters `u`), leaving along `t1`, arriving along `t2`."""
    a1 = 3 * (1 - u)[:, None] ** 2 * u[:, None] * t1
    a2 = 3 * (1 - u)[:, None] * u[:, None] ** 2 * t2
    gram = np.array([[np.sum(a1 * a1), np.sum(a1 * a2)], [np.sum(a1 * a2), np.sum(a2 * a2)]])
    base = _bez(np.array([p[0], p[0], p[-1], p[-1]]), u)
    tmp = p - base
    rhs = np.array([np.sum(a1 * tmp), np.sum(a2 * tmp)])
    det = gram[0, 0] * gram[1, 1] - gram[0, 1] * gram[1, 0]
    seg = np.linalg.norm(p[-1] - p[0])
    if abs(det) > _EPS:
        al = (rhs[0] * gram[1, 1] - rhs[1] * gram[0, 1]) / det
        ar = (gram[0, 0] * rhs[1] - gram[1, 0] * rhs[0]) / det
    else:
        al = ar = 0
    eps = 1e-6 * seg
    # A handle longer than the whole polyline it fits is nonsense (an ill-conditioned least squares
    # when the points double back, e.g. a spliced curl): fall back to the standard chord/3 handles
    # instead of letting a control point fly off thousands of font units away.
    path_len = float(np.hypot(*np.diff(p, axis=0).T).sum())
    if al < eps or ar < eps or al > path_len or ar > path_len:
        al = ar = seg / 3
    return np.array([p[0], p[0] + t1 * al, p[-1] + t2 * ar, p[-1]])


def _reparam(c: np.ndarray, p: np.ndarray, u: np.ndarray) -> np.ndarray:
    """One Newton-Raphson step improving the parameters `u` of `p` on the cubic `c`."""
    d1, d2 = _bez_d1(c, u), _bez_d2(c, u)
    diff = _bez(c, u) - p
    num = np.sum(diff * d1, axis=1)
    den = np.sum(d1 * d1, axis=1) + np.sum(diff * d2, axis=1)
    den[np.abs(den) < 1e-12] = 1e-12
    return np.clip(u - num / den, 0, 1)


def fit_cubic(
    p: np.ndarray, t1: np.ndarray, t2: np.ndarray, err: float, depth: int = 0
) -> list[np.ndarray]:
    """Fit `p` with as few cubic Beziers as keep every point within `err`.

    Parameters
    ----------
    p : np.ndarray
        ``(n, 2)`` points to fit.
    t1, t2 : np.ndarray
        Unit tangents at the start and the end.
    err : float
        Largest allowed distance from any point to the curve, in font units.
    depth : int
        Recursion depth (internal).

    Returns
    -------
    list[np.ndarray]
        Cubics, each a ``(4, 2)`` array of control points.
    """
    if len(p) == 2:
        d = np.linalg.norm(p[1] - p[0]) / 3
        return [np.array([p[0], p[0] + t1 * d, p[1] + t2 * d, p[1]])]
    u = _chord_param(p)
    c = _generate(p, u, t1, t2)
    for _ in range(4):
        dist = np.sum((_bez(c, u) - p) ** 2, axis=1)
        if dist.max() < err**2:
            return [c]
        u = _reparam(c, p, u)
        c = _generate(p, u, t1, t2)
    dist = np.sum((_bez(c, u) - p) ** 2, axis=1)
    if dist.max() < err**2 or depth > 8 or len(p) < 6:
        return [c]
    split = int(np.argmax(dist))
    split = min(max(split, 2), len(p) - 3)
    tc = unit(p[split - 1] - p[split + 1])
    left = fit_cubic(p[: split + 1], t1, tc, err, depth + 1)
    return left + fit_cubic(p[split:], -tc, t2, err, depth + 1)


def fit_polyline(p: np.ndarray, err: float) -> list[np.ndarray]:
    """Fit `p` with cubics, taking the end tangents from the polyline itself.

    Parameters
    ----------
    p : np.ndarray
        ``(n, 2)`` points to fit.
    err : float
        Largest allowed distance from any point to the curve, in font units.

    Returns
    -------
    list[np.ndarray]
        Cubics, each a ``(4, 2)`` array of control points.
    """
    k = min(4, len(p) - 1)
    t1, t2 = unit(p[k] - p[0]), unit(p[-1 - k] - p[-1])
    return fit_cubic(p, t1, t2, err)


def fit_with_tangents(
    p: np.ndarray,
    err: float,
    t_start: np.ndarray | None = None,
    t_end: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Fit `p`, optionally with exact unit tangents at either end (for a G1 join to a line).

    Parameters
    ----------
    p : np.ndarray
        ``(n, 2)`` points to fit.
    err : float
        Largest allowed distance from any point to the curve, in font units.
    t_start : np.ndarray | None
        Exact unit tangent at the start (``None`` takes it from the points).
    t_end : np.ndarray | None
        Exact unit tangent at the end (``None`` takes it from the points).

    Returns
    -------
    list[np.ndarray]
        Cubics, each a ``(4, 2)`` array of control points.
    """
    k = min(4, len(p) - 1)
    t1 = unit(t_start) if t_start is not None else unit(p[k] - p[0])
    t2 = unit(t_end) if t_end is not None else unit(p[-1 - k] - p[-1])
    return fit_cubic(p, t1, t2, err)


def line_bezier(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return the cubic that is exactly the straight segment a -> b.

    Parameters
    ----------
    a : np.ndarray
        Start point ``(x, y)``, in font units.
    b : np.ndarray
        End point ``(x, y)``, in font units.

    Returns
    -------
    np.ndarray
        The ``(4, 2)`` control points.
    """
    return np.array([a, a + (b - a) / 3, a + 2 * (b - a) / 3, b])


def beziers_to_d(segs_per_piece: list[list[np.ndarray]]) -> str:
    """Serialise pieces of cubics as one SVG path string (one decimal place).

    Parameters
    ----------
    segs_per_piece : list[list[np.ndarray]]
        Pieces of cubic Beziers, each a list of ``(4, 2)`` control-point arrays.

    Returns
    -------
    str
        The path's ``d`` attribute.
    """
    first = segs_per_piece[0][0][0]
    parts = [f"M {first[0]:.1f} {first[1]:.1f}"]
    for segs in segs_per_piece:
        for c in segs:
            parts.append("C " + " ".join(f"{v:.1f}" for v in (*c[1], *c[2], *c[3])))
    return " ".join(parts)
