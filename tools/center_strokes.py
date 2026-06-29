#!/usr/bin/env python3
"""Translate hand-authored strokes so their bounding-box centre aligns with the ghost glyph centre.

Usage (from repo root):
    cd python && poetry run python ../tools/center_strokes.py

Reads:  js/src/stroke-data.json  +  js/src/glyph-data.json
Writes: js/src/stroke-data-centered.json
"""

from __future__ import annotations

import json
from pathlib import Path

import svgpathtools

ROOT = Path(__file__).resolve().parent.parent
GLYPH_DATA = ROOT / "js" / "src" / "glyph-data.json"
STROKE_DATA = ROOT / "js" / "src" / "stroke-data-snapped.json"
OUT_PATH = ROOT / "js" / "src" / "stroke-data-centered.json"

N = 200  # sample points per path when estimating bounding box


def bbox_center(paths: list[tuple[str, float, float]]) -> tuple[float, float] | None:
    """Return (cx, cy) bounding-box centre of all sampled points.

    Each entry in *paths* is (d, dx, dy) where dx/dy is the glyph component offset.
    """
    xs: list[float] = []
    ys: list[float] = []
    for d, dx, dy in paths:
        try:
            path = svgpathtools.parse_path(d)
        except Exception:
            continue
        length = path.length()
        if length <= 0:
            continue
        for i in range(N):
            p = path.point(i / (N - 1))
            xs.append(p.real + dx)
            ys.append(p.imag + dy)
    if not xs:
        return None
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def translate_d(d: str, dx: float, dy: float) -> str:
    """Translate every point in an SVG path string by (dx, dy)."""
    path = svgpathtools.parse_path(d)
    delta = complex(dx, dy)
    translated = svgpathtools.Path(*[seg.translated(delta) for seg in path])
    return translated.d()


def main() -> None:
    glyph_data = json.loads(GLYPH_DATA.read_text(encoding="utf-8"))
    stroke_data = json.loads(STROKE_DATA.read_text(encoding="utf-8"))
    out: dict = {}

    for cluster, entry in stroke_data.items():
        ghost_paths = [
            (g["d"], g.get("x", 0), g.get("y", 0))
            for g in glyph_data["clusters"].get(cluster, {}).get("glyphs", [])
        ]
        ghost_c = bbox_center(ghost_paths)

        stroke_paths = [(s["d"], 0.0, 0.0) for s in entry.get("strokes", [])]
        stroke_c = bbox_center(stroke_paths)

        if ghost_c is None or stroke_c is None:
            out[cluster] = entry
            print(f"  {cluster!r}: skipped (no paths to sample)")
            continue

        dx = ghost_c[0] - stroke_c[0]
        dy = ghost_c[1] - stroke_c[1]
        print(f"  {cluster!r}: shift ({dx:+.1f}, {dy:+.1f})")

        out[cluster] = {
            "strokes": [{"d": translate_d(s["d"], dx, dy)} for s in entry["strokes"]]
        }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
