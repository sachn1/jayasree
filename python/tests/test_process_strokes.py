"""Tests for tools/process_strokes.py: how a recorded stroke is guided by its outline."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import process_strokes  # noqa: E402

from jayasree import geometry  # noqa: E402

JS_SRC = ROOT / "js" / "src"


def _worst_move(a: list[dict], b: list[dict]) -> float:
    """Return how far the strokes `a` have moved from `b`: the largest nearest-point distance."""
    pts_a = np.array([p for s in a for p in geometry.sample_path(s["d"], 80)])
    pts_b = np.array([p for s in b for p in geometry.sample_path(s["d"], 80)])
    return float(np.sqrt(((pts_a[:, None] - pts_b[None]) ** 2).sum(axis=2)).min(axis=1).max())


def test_straightening_does_not_snap_a_long_stroke_onto_a_short_edge() -> None:
    """Ensure that പൃ's flat bar is not turned into a diagonal by the straightening stage."""
    glyphs = json.loads((JS_SRC / "glyph-data.json").read_text("utf-8"))
    raw = json.loads((JS_SRC / "stroke-data.raw.json").read_text("utf-8"))["പൃ"]
    smoothed = process_strokes._process_cluster_strokes(
        "പൃ", raw, glyphs, Namespace(center=True, smooth=True, straighten=False), "ml"
    )
    straightened = process_strokes._process_cluster_strokes(
        "പൃ", raw, glyphs, Namespace(center=True, smooth=True, straighten=True), "ml"
    )
    # before the length check the straightened strokes were 129 units from the smoothed ones
    assert _worst_move(straightened, smoothed) < 60


def _process(cluster: str, lang: str = "ml", **stages: bool) -> list[dict]:
    glyphs = json.loads((JS_SRC / "glyph-data.json").read_text("utf-8"))
    raw = json.loads((JS_SRC / "stroke-data.raw.json").read_text("utf-8"))[cluster]
    args = Namespace(**{"center": False, "smooth": False, "straighten": False, **stages})
    return process_strokes._process_cluster_strokes(cluster, raw, glyphs, args, lang)


@pytest.mark.parametrize("mark", ["്വ", "്യ", "്ല"])  # ്വ ്യ ്ല
def test_a_suffix_mark_without_a_cluster_is_guided_by_its_own_outline(mark: str) -> None:
    """Ensure that a mark with no cluster entry is still centred and straightened."""
    guided = _process(mark, center=True, smooth=True, straighten=True)
    unguided = _process(mark, center=False, smooth=True, straighten=False)
    assert guided != unguided


def test_a_mark_without_a_cluster_is_not_guided_for_another_language() -> None:
    """Ensure that the mark-outline guide is Malayalam's alone."""
    other = _process("്വ", lang="hi", center=True, smooth=True, straighten=True)
    unguided = _process("്വ", center=False, smooth=True, straighten=False)
    assert other == unguided
