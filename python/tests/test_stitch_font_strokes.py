"""Tests for tools/stitch_font_strokes.py: splitting a cluster and placing letters inside it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import stitch_font_strokes as sfs  # noqa: E402

BAR = "M 0 0 L 600 0 L 600 300 L 0 300 Z"
ATOMS = {"a": {"strokes": []}, "b": {"strokes": []}, "ab": {"strokes": []}}


def _glyph(d: str, x: float = 0.0, y: float = 0.0) -> dict:
    return {"d": d, "x": x, "y": y}


def _glyph_data() -> dict:
    return {
        "clusters": {
            "a": {"glyphs": [_glyph(BAR)]},
            "b": {"glyphs": [_glyph(BAR)]},
            "a്b": {"glyphs": [_glyph(BAR), _glyph(BAR, 0, 700)]},
        },
        "marks": {},
    }


def test_parts_of_splits_into_chosen_letters_skipping_the_virama() -> None:
    """Ensure that a conjunct splits into the letters that have chosen strokes."""
    atoms = {"a": {}, "b": {}}
    assert sfs.parts_of("a്b", atoms) == ["a", "b"]


def test_parts_of_is_none_when_a_letter_has_no_strokes() -> None:
    """Ensure that a cluster with an unchosen piece is not guessed at."""
    assert sfs.parts_of("a്z", {"a": {}}) is None


def test_parts_of_is_none_for_a_single_letter() -> None:
    """Ensure that a lone letter is not stitched from itself."""
    assert sfs.parts_of("a", {"a": {}}) is None


def test_stitch_cluster_moves_each_letter_onto_its_place() -> None:
    """Ensure that two stacked bars are stitched from one bar stroke placed twice."""
    atoms = {
        "a": {"strokes": [{"d": "M 0 150 L 600 150"}]},
        "b": {"strokes": [{"d": "M 0 150 L 600 150"}]},
    }
    strokes, share, _ = sfs.stitch_cluster("a്b", _glyph_data(), atoms, {})
    assert strokes is not None and len(strokes) == 2
    assert share >= sfs.MIN_COVER
    ys = sorted(parse_path(d).start.imag for d in strokes)
    assert ys[1] - ys[0] == pytest.approx(700, abs=60)


def test_stitch_cluster_reports_a_letter_that_has_no_strokes() -> None:
    """Ensure that a missing letter is reported rather than stitched around."""
    strokes, _, note = sfs.stitch_cluster("a്b", _glyph_data(), {"a": {"strokes": []}}, {})
    assert strokes is None
    assert "no chosen strokes" in note


def test_close_gaps_pulls_a_part_towards_the_ones_before_it() -> None:
    """Ensure that a part sitting far to the side is moved until only the gap is left."""
    left = ["M 0 0 L 100 0"]
    right = ["M 500 0 L 600 0"]
    out = sfs.close_gaps([left, right], 50)
    assert parse_path(out[1]).bbox()[0] == pytest.approx(150)


def test_close_gaps_leaves_a_part_that_is_already_close() -> None:
    """Ensure that a part nearer than the gap is not pushed away."""
    out = sfs.close_gaps([["M 0 0 L 100 0"], ["M 120 0 L 200 0"]], 50)
    assert parse_path(out[1]).bbox()[0] == pytest.approx(120)
