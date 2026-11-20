"""Audit cleaned strokes against the recordings they came from.

A cleanup can introduce a *kink*: a sharper bend than the human ever drew. This module measures
that for each stroke, so the worst ones can be looked at first instead of every letter. Three
numbers per stroke:

* **bend**: the sharpest local turn along the path, in degrees (the very ends excluded). The
  human's path is smoothed first so hand tremor does not count as a bend; the cleaned path is not.
  ``excess = bend_cleaned - bend_human``: a large positive excess is the signature of a kink the
  cleanup introduced (a corner the human rounded, a join between a line and a curve).
* **flips**: how many times the cleaned path's curvature changes sign. A wobbly stroke flips a
  lot; a clean curve flips as often as its letterform does.
* **deviation**: the largest distance from any recorded point to the cleaned path, in font units.
  Large means the cleanup skipped a loop or a limb the human drew.

These are heuristics for *ranking*, not a verdict: a flagged stroke may be fine and an unflagged
one ugly. Known limits: a corner the human really drew sharply reads as positive excess (only the
recording is smoothed), and a stem drawn up then straight back down is a deliberate 180-degree
reversal, not a kink. The owner's eye on the review list is the gate.
"""

from __future__ import annotations

import numpy as np
import svgpathtools
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from jayasree.cleanup.fitting import resample

#: Resampling step (font units) for measuring bends.
SPACING_FU = 4.0
#: A "local" bend: turning across this much path either side of a point.
WINDOW_FU = 12.0
#: Ignore the very ends of a stroke: a start or end hook is not a kink.
EDGE_FU = 20.0
#: Smoothing applied to the human's path so hand tremor does not count as a bend.
TREMOR_SIGMA_FU = 8.0
#: A stroke is flagged when its sharpest bend exceeds the human's by more than this many degrees.
KINK_EXCESS_DEG = 25.0
#: Curvature below this (radians per sample) is noise and does not count toward a flip.
_NOISE_CURVATURE = 0.03


def sample(d: str, n: int = 600) -> np.ndarray:
    """Return about `n` points along the SVG path `d`, spread over its segments by length.

    Each segment is evaluated in one vectorized step, which is far faster than sampling the whole
    path point by point (``geometry.sample_path`` costs about a second per stroke - too slow to
    audit hundreds of strokes). The spacing is only roughly even; every measure here resamples
    to an even spacing itself.
    """
    segments = list(svgpathtools.parse_path(d))
    lengths = np.array([max(seg.length(), 1e-9) for seg in segments])
    counts = np.maximum(3, np.ceil(n * lengths / lengths.sum()).astype(int))
    parts = [seg.poly()(np.linspace(0.0, 1.0, k)) for seg, k in zip(segments, counts, strict=True)]
    pts = np.concatenate([np.column_stack([p.real, p.imag]) for p in parts])
    return pts


def max_bend(points: np.ndarray, smooth_sigma_fu: float = 0.0) -> float:
    """Return the sharpest local turn, in degrees, anywhere along a path (ends excluded).

    Parameters
    ----------
    points : np.ndarray
        ``(n, 2)`` points along the path.
    smooth_sigma_fu : float
        If positive, Gaussian-smooth the path first (used on a recording to remove tremor).

    Returns
    -------
    float
        The largest turn between the stretch before and the stretch after a point, 0 for a path
        too short to measure.
    """
    p = resample(points, SPACING_FU)
    if len(p) < 8:
        return 0.0
    if smooth_sigma_fu > 0:
        sigma = smooth_sigma_fu / SPACING_FU
        p = np.column_stack([gaussian_filter1d(p[:, i], sigma, mode="nearest") for i in (0, 1)])
    k = max(2, round(WINDOW_FU / SPACING_FU))
    edge = round(EDGE_FU / SPACING_FU)
    worst = 0.0
    for i in range(max(k, edge), len(p) - max(k, edge) - 1):
        a, b = p[i] - p[i - k], p[i + k] - p[i]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom < 1e-9:
            continue
        worst = max(worst, float(np.degrees(np.arccos(np.clip(a @ b / denom, -1.0, 1.0)))))
    return worst


def curvature_flips(points: np.ndarray) -> int:
    """Return how many times the path through `points` changes the way it curves (no noise)."""
    p = resample(points, 6.0)
    tangent = np.diff(p, axis=0)
    angle = np.unwrap(np.arctan2(tangent[:, 1], tangent[:, 0]))
    curvature = np.diff(angle)
    big = curvature[np.abs(curvature) > _NOISE_CURVATURE]
    return int(np.sum(np.diff(np.sign(big)) != 0)) if len(big) > 1 else 0


def max_deviation(recorded: np.ndarray, cleaned: np.ndarray) -> float:
    """Return the largest distance (font units) from any recorded point to the cleaned path."""
    return float(cKDTree(cleaned).query(recorded)[0].max())


def audit_stroke(raw_d: str, cleaned_d: str) -> dict:
    """Measure one cleaned stroke against its recording.

    Returns
    -------
    dict
        ``bend_human``, ``bend_cleaned``, ``excess``, ``flips`` and ``max_dev_fu``, rounded.
    """
    recorded, cleaned = sample(raw_d, 600), sample(cleaned_d, 800)
    bend_human = max_bend(recorded, TREMOR_SIGMA_FU)
    bend_cleaned = max_bend(cleaned)
    return {
        "bend_human": round(bend_human, 1),
        "bend_cleaned": round(bend_cleaned, 1),
        "excess": round(bend_cleaned - bend_human, 1),
        "flips": curvature_flips(cleaned),
        "max_dev_fu": round(max_deviation(recorded, cleaned), 1),
    }


def audit_atoms(raw: dict, processed: dict) -> list[dict]:
    """Audit every recorded atom's strokes and return the rows, worst excess first.

    Parameters
    ----------
    raw : dict
        ``stroke-data.<code>.raw.json``: the recordings.
    processed : dict
        ``stroke-data.<code>.json``: what ships.

    Returns
    -------
    list[dict]
        One row per stroke: ``atom``, ``stroke`` (1-based), ``unchanged`` (the shipped stroke is
        the recording itself) and the :func:`audit_stroke` numbers. An atom whose stroke count
        differs between the two files is reported with ``stroke_count_mismatch`` instead.
    """
    rows = []
    for atom, entry in raw.items():
        if atom == "_remarks" or atom not in processed:
            continue
        recorded = [s["d"] for s in entry["strokes"]]
        shipped = [s["d"] for s in processed[atom]["strokes"]]
        if len(recorded) != len(shipped):
            rows.append({"atom": atom, "stroke_count_mismatch": [len(recorded), len(shipped)]})
            continue
        for index, (raw_d, new_d) in enumerate(zip(recorded, shipped, strict=True), 1):
            rows.append(
                {"atom": atom, "stroke": index, "unchanged": raw_d == new_d}
                | audit_stroke(raw_d, new_d)
            )
    return sorted(rows, key=lambda r: -r.get("excess", float("inf")))
