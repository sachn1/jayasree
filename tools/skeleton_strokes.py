#!/usr/bin/env python3
"""Nudge hand-authored strokes toward the medial axis of the Manjari ghost glyph.

Steps per cluster:
  1. Rasterize the filled ghost outline using its *actual* tight bounding box
     (not the full ascent/descent range) so every pixel maps to a smaller
     font-unit region → finer, more accurate skeleton.
  2. Compute medial axis (distance-transform ridge) → mathematical centerline.
  3. KD-tree of skeleton pixels in font units.
  4. For each stroke point within SNAP_RADIUS, pull it toward the nearest
     skeleton point by SNAP_ALPHA. Points further away are left unchanged
     to avoid teleporting to wrong branches.
  5. Fit a smooth cubic bezier through the nudged points.
  6. Write stroke-data-skeleton.json. stroke-data.json is never modified.

Usage (from repo root):
    cd python && poetry run python ../tools/skeleton_strokes.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import svgpathtools
from PIL import Image, ImageDraw
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree
from skimage.morphology import medial_axis

ROOT = Path(__file__).resolve().parent.parent
GLYPH_DATA = ROOT / "js" / "src" / "glyph-data.json"
STROKE_DATA = ROOT / "js" / "src" / "stroke-data.json"
OUT_PATH = ROOT / "js" / "src" / "stroke-data-skeleton.json"

RASTER_SIZE = 1024   # px — larger = finer skeleton
BBOX_PAD = 80.0      # font units of padding around the outline bbox
N_STROKE_SAMPLES = 150
N_OUT = 50
SNAP_RADIUS = 300.0  # font units — ~15% of 2048 UPM
SNAP_ALPHA = 0.85    # 0=no change, 1=full snap to skeleton


# ---------------------------------------------------------------------------
# Rasterise glyph outline using tight bounding box
# ---------------------------------------------------------------------------

def outline_to_bitmap(glyph_glyphs: list[dict]) -> tuple[np.ndarray, float, float, float, float]:
    """Rasterize component outlines to a binary bitmap, using the outline's
    own bounding box as the viewport for maximum pixel density."""
    all_pts: list[tuple[float, float]] = []
    comp_polys: list[list[tuple[float, float]]] = []

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
            n_pts = max(64, int(length / 5))
            pts = [(sub.point(i / n_pts).real + dx, sub.point(i / n_pts).imag + dy)
                   for i in range(n_pts + 1)]
            all_pts.extend(pts)
            comp_polys.append(pts)

    if not all_pts:
        return np.zeros((RASTER_SIZE, RASTER_SIZE), dtype=bool), 0.0, 0.0, 1.0, 1.0

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    x_min, x_max = min(xs) - BBOX_PAD, max(xs) + BBOX_PAD
    y_min, y_max = min(ys) - BBOX_PAD, max(ys) + BBOX_PAD
    w, h = x_max - x_min, y_max - y_min

    img = Image.new("L", (RASTER_SIZE, RASTER_SIZE), 0)
    draw = ImageDraw.Draw(img)

    def to_px(fx: float, fy: float) -> tuple[float, float]:
        return (fx - x_min) / w * RASTER_SIZE, (y_max - fy) / h * RASTER_SIZE  # y flipped

    for poly_pts in comp_polys:
        poly = [to_px(px, py) for px, py in poly_pts]
        if len(poly) >= 3:
            draw.polygon(poly, fill=255)

    return np.array(img) > 128, x_min, y_min, x_max, y_max


# ---------------------------------------------------------------------------
# Sample stroke path
# ---------------------------------------------------------------------------

def sample_stroke(d: str, n: int) -> np.ndarray:
    try:
        path = svgpathtools.parse_path(d)
    except Exception:
        return np.empty((0, 2))
    length = path.length()
    if length <= 0:
        return np.empty((0, 2))
    pts = []
    for i in range(n):
        try:
            t = path.ilength(i / (n - 1) * length)
        except Exception:
            t = i / (n - 1)
        p = path.point(t)
        pts.append((p.real, p.imag))
    return np.array(pts)


# ---------------------------------------------------------------------------
# Fit smooth bezier
# ---------------------------------------------------------------------------

def fit_bezier(pts: np.ndarray) -> str:
    if len(pts) < 4:
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)

    x, y = pts[:, 0], pts[:, 1]
    keep = np.ones(len(x), dtype=bool)
    for i in range(1, len(x)):
        if abs(x[i] - x[i - 1]) < 0.5 and abs(y[i] - y[i - 1]) < 0.5:
            keep[i] = False
    x, y = x[keep], y[keep]
    if len(x) < 4:
        return "M " + " L ".join(f"{xi:.1f} {yi:.1f}" for xi, yi in zip(x, y))

    try:
        tck, _ = splprep([x, y], s=len(x) * 0.5, k=3)
    except Exception:
        try:
            tck, _ = splprep([x, y], s=0, k=3)
        except Exception:
            return "M " + " L ".join(f"{xi:.1f} {yi:.1f}" for xi, yi in zip(x, y))

    u = np.linspace(0, 1, N_OUT)
    xs, ys = splev(u, tck)
    dxs, dys = splev(u, tck, der=1)
    dt = 1.0 / (N_OUT - 1)
    parts = [f"M {xs[0]:.1f} {ys[0]:.1f}"]
    for i in range(N_OUT - 1):
        parts.append(
            f"C {xs[i] + dxs[i]*dt/3:.1f} {ys[i] + dys[i]*dt/3:.1f}"
            f" {xs[i+1] - dxs[i+1]*dt/3:.1f} {ys[i+1] - dys[i+1]*dt/3:.1f}"
            f" {xs[i+1]:.1f} {ys[i+1]:.1f}"
        )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    glyph_data = json.loads(GLYPH_DATA.read_text(encoding="utf-8"))
    stroke_data = json.loads(STROKE_DATA.read_text(encoding="utf-8"))
    out: dict = {}

    for cluster, entry in stroke_data.items():
        cluster_info = glyph_data["clusters"].get(cluster)
        if cluster_info is None:
            out[cluster] = entry
            print(f"  {cluster!r}: no ghost — kept as-is")
            continue

        bitmap, x_min, y_min, x_max, y_max = outline_to_bitmap(cluster_info["glyphs"])
        skel, _ = medial_axis(bitmap, return_distance=True)
        skel_rows, skel_cols = np.where(skel)

        if len(skel_rows) == 0:
            out[cluster] = entry
            print(f"  {cluster!r}: empty skeleton — kept as-is")
            continue

        w, h = x_max - x_min, y_max - y_min
        skel_fx = skel_cols / RASTER_SIZE * w + x_min
        skel_fy = y_max - skel_rows / RASTER_SIZE * h  # flip y back
        skel_pts = np.column_stack([skel_fx, skel_fy])
        tree = cKDTree(skel_pts)

        new_strokes = []
        for stroke in entry.get("strokes", []):
            raw_pts = sample_stroke(stroke["d"], N_STROKE_SAMPLES)
            if len(raw_pts) == 0:
                new_strokes.append(stroke)
                continue

            dists, idx = tree.query(raw_pts)
            nudged = raw_pts.copy()
            within = dists < SNAP_RADIUS
            nudged[within] = (
                raw_pts[within] * (1 - SNAP_ALPHA)
                + skel_pts[idx[within]] * SNAP_ALPHA
            )
            print(f"  {cluster!r}: {within.sum()/len(raw_pts)*100:.0f}% of points nudged"
                  f"  (median dist {np.median(dists):.0f} fu, radius={SNAP_RADIUS})")

            new_strokes.append({"d": fit_bezier(nudged)})

        out[cluster] = {"strokes": new_strokes}

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
