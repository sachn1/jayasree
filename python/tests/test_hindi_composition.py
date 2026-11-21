"""Tests for the Hindi-only build steps: conjunct + vowel-sign clusters.

Both live in ``tools/`` and are gated on ``lang.code == "hi"``, so Malayalam never runs them (the
Malayalam freeze, ``test_malayalam_freeze.py``, covers that side). The shaping is stubbed here: what
is under test is the decision logic (which clusters get an entry, and whether it carries a
``markNudge``), not HarfBuzz.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_glyph_data  # noqa: E402

VIRAMA = "\u094d"
MARK = "\u0941"  # ु
KA, KHA = "\u0915", "\u0916"
BASE_KEY = KA + VIRAMA + KHA
CHARS = SimpleNamespace(CONSONANTS=(KA, KHA), VIRAMA=VIRAMA)

BASE_GLYPH = {"d": "M0 0 L10 10", "x": 0.0, "y": 0.0}
MARK_GLYPH = {"d": "M1 1 L2 2", "x": 100.0, "y": 5.0}
BASE_ADVANCE = 500.0
SHIFT = 0.0
GENERIC_X = SHIFT + BASE_ADVANCE + MARK_GLYPH["x"]  # where the generic recipe puts the mark

SHAPED = {
    "clusters": {BASE_KEY: {"glyphs": [BASE_GLYPH], "advance": BASE_ADVANCE}},
    "marks": {MARK: {"prefix": [], "suffix": [MARK_GLYPH], "shift": SHIFT}},
}


def _stub_shaping(
    monkeypatch: pytest.MonkeyPatch, glyphs: list[dict], advance: float = 600.0
) -> None:
    """Make `shape_word` return `glyphs` for every cluster."""
    trace = {"glyphs": glyphs, "totalAdvance": advance}
    monkeypatch.setattr(build_glyph_data, "shape_word", lambda cluster, font: trace)


class TestHindiConjunctMarkClusters:
    """_hi_conjunct_mark_clusters: which conjunct + vowel-sign clusters get a real entry."""

    def test_cluster_the_generic_recipe_already_gets_right_is_left_to_runtime(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure that a mark where the generic recipe puts it adds no entry."""
        _stub_shaping(monkeypatch, [BASE_GLYPH, {**MARK_GLYPH, "x": GENERIC_X}])
        assert build_glyph_data._hi_conjunct_mark_clusters(CHARS, SHAPED, "font") == {}

    def test_moved_mark_gets_an_entry_with_the_offset_as_nudge(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure that a mark the font places elsewhere is kept, with its offset as dx/dy."""
        moved = {**MARK_GLYPH, "x": GENERIC_X + 30.0, "y": MARK_GLYPH["y"] - 80.0}
        _stub_shaping(monkeypatch, [BASE_GLYPH, moved], advance=640.0)
        added = build_glyph_data._hi_conjunct_mark_clusters(CHARS, SHAPED, "font")
        assert added == {
            BASE_KEY + MARK: {
                "glyphs": [BASE_GLYPH, moved],
                "advance": 640.0,
                "markNudge": {"dx": 30.0, "dy": -80.0},
            }
        }

    def test_fused_glyphs_get_an_entry_without_a_nudge(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure that a mark the font merged into the base glyphs has a ghost but no nudge."""
        fused = {"d": "M9 9 L8 8", "x": 0.0, "y": 0.0}
        _stub_shaping(monkeypatch, [fused])
        added = build_glyph_data._hi_conjunct_mark_clusters(CHARS, SHAPED, "font")
        assert list(added) == [BASE_KEY + MARK]
        assert "markNudge" not in added[BASE_KEY + MARK]

    def test_a_script_without_a_virama_adds_nothing(self) -> None:
        """Ensure that a character inventory with no virama is skipped, not an error."""
        no_virama = SimpleNamespace(CONSONANTS=(KA, KHA))
        assert build_glyph_data._hi_conjunct_mark_clusters(no_virama, SHAPED, "font") == {}

    def test_prefix_marks_are_not_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure that a mark rendered before its base (prefix) is not handled here."""
        _stub_shaping(monkeypatch, [BASE_GLYPH, MARK_GLYPH])
        prefix = {**SHAPED, "marks": {MARK: {"prefix": [MARK_GLYPH], "suffix": [], "shift": 0.0}}}
        assert build_glyph_data._hi_conjunct_mark_clusters(CHARS, prefix, "font") == {}

    def test_shaping_failure_skips_that_cluster(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Ensure that a cluster the font cannot shape is reported and skipped."""

        def boom(cluster: str, font: str) -> dict:
            raise RuntimeError("no glyph")

        monkeypatch.setattr(build_glyph_data, "shape_word", boom)
        assert build_glyph_data._hi_conjunct_mark_clusters(CHARS, SHAPED, "font") == {}
        assert "skip" in capsys.readouterr().err


@pytest.fixture(scope="module")
def hindi_clusters() -> dict:
    """Hindi's committed cluster table."""
    data = json.loads((ROOT / "js" / "src" / "glyph-data.hi.json").read_text(encoding="utf-8"))
    return data["clusters"]


class TestCommittedHindiConjunctData:
    """The committed glyph-data.hi.json's real-shaped conjunct + vowel-sign entries."""

    def test_every_nudge_belongs_to_a_conjunct_with_a_known_base(
        self, hindi_clusters: dict
    ) -> None:
        """Ensure that each markNudge entry is a base conjunct + mark with its base also present."""
        clusters = hindi_clusters
        nudged = {c: e for c, e in clusters.items() if "markNudge" in e}
        assert len(nudged) > 500, "the conjunct + vowel-sign entries are missing"
        for cluster, entry in nudged.items():
            assert cluster[-1] in "\u0941\u0942\u0943", cluster
            assert cluster[:-1] in clusters, cluster
            assert len(entry["glyphs"]) == len(clusters[cluster[:-1]]["glyphs"]) + 1, cluster
