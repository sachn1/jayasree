"""Tests for jayasree.cleanup.audit - ranking cleaned strokes by how likely they hold a kink.

Script-agnostic: strokes here are synthetic lines, corners and waves.
"""

from __future__ import annotations

import numpy as np
import pytest

from jayasree.cleanup import audit

STRAIGHT = "M 0 0 L 300 0"
RIGHT_ANGLE = "M 0 0 L 150 0 L 150 150"
WAVE = "M 0 0 " + " ".join(f"L {x} {30 * np.sin(x / 25):.1f}" for x in range(10, 400, 10))
ARC = "M 0 0 C 0 110 110 220 220 220"


class TestSample:
    """sample: fast, length-weighted points along a path."""

    @pytest.mark.parametrize("empty", ["", "M 0 0"])
    def test_a_path_with_no_segments_is_a_value_error(self, empty: str) -> None:
        """Ensure that an empty or move-only path is a clear ValueError."""
        with pytest.raises(ValueError, match="no segments"):
            audit.sample(empty)

    def test_handles_an_arc_segment(self) -> None:
        """Ensure that an SVG arc segment samples to points on the arc."""
        pts = audit.sample("M 0 0 A 50 50 0 0 1 100 0", 200)
        assert np.allclose(pts[0], [0, 0]) and np.allclose(pts[-1], [100, 0], atol=1e-6)
        assert np.abs(pts[:, 1]).max() == pytest.approx(50.0, abs=1.0)

    def test_covers_the_whole_path_end_to_end(self) -> None:
        """Ensure that the first and last points are the path's ends."""
        pts = audit.sample("M 0 0 L 100 0 L 100 100")
        assert np.allclose(pts[0], [0, 0]) and np.allclose(pts[-1], [100, 100])

    def test_spreads_points_by_length_and_follows_curves(self) -> None:
        """Ensure that a cubic is sampled along its curve, not its chord."""
        pts = audit.sample("M 0 0 C 0 100 100 100 100 0", 200)
        assert pts[:, 1].max() == pytest.approx(75.0, abs=1.0)
        assert len(pts) >= 150


class TestMeasures:
    """max_bend, curvature_flips and max_deviation."""

    def test_a_straight_line_has_no_bend(self) -> None:
        """Ensure that a straight path scores 0."""
        assert audit.max_bend(audit.sample(STRAIGHT)) == pytest.approx(0.0, abs=1.0)

    def test_a_right_angle_scores_about_ninety_degrees(self) -> None:
        """Ensure that a sharp corner is measured at roughly its angle."""
        assert audit.max_bend(audit.sample(RIGHT_ANGLE)) == pytest.approx(90.0, abs=20.0)

    def test_smoothing_the_recording_lowers_its_bend(self) -> None:
        """Ensure that tremor smoothing reduces a sharp corner's measured bend."""
        pts = audit.sample(RIGHT_ANGLE)
        assert audit.max_bend(pts, audit.TREMOR_SIGMA_FU) < audit.max_bend(pts)

    def test_a_too_short_path_scores_zero(self) -> None:
        """Ensure that a path too short to measure does not raise."""
        assert audit.max_bend(np.array([[0.0, 0.0], [3.0, 0.0], [6.0, 0.0]])) == 0.0

    def test_a_wave_flips_curvature_and_an_arc_does_not(self) -> None:
        """Ensure that a wobbly path has many flips and a clean arc has none."""
        assert audit.curvature_flips(audit.sample(WAVE, 800)) == 4
        assert audit.curvature_flips(audit.sample(ARC, 400)) == 0
        assert audit.curvature_flips(audit.sample(STRAIGHT, 400)) == 0

    def test_deviation_also_catches_a_limb_the_cleanup_added(self) -> None:
        """Ensure that a cleaned path with an extra limb scores high, not just a skipped one."""
        recorded = audit.sample("M 0 0 L 400 0", 400)
        cleaned = audit.sample("M 0 0 L 200 0 L 200 100 L 200 0 L 400 0", 400)
        assert audit.max_deviation(recorded, cleaned) == pytest.approx(100.0, abs=1.0)
        assert audit.max_deviation(cleaned, recorded) == pytest.approx(100.0, abs=1.0)

    def test_deviation_is_the_largest_gap_to_the_cleaned_path(self) -> None:
        """Ensure that a recorded point 20 units off the cleaned path gives 20."""
        cleaned = audit.sample(STRAIGHT, 400)
        recorded = audit.sample("M 0 0 L 150 20 L 300 0", 400)
        assert audit.max_deviation(recorded, cleaned) == pytest.approx(20.0, abs=1.0)


class TestAudit:
    """audit_stroke and audit_atoms."""

    def test_an_unchanged_gentle_stroke_has_no_excess(self) -> None:
        """Ensure that auditing a gentle curve against itself shows no introduced bend."""
        row = audit.audit_stroke(ARC, ARC)
        assert row["max_dev_fu"] < 1.0 and row["excess"] <= 1.0

    def test_a_sharp_corner_the_human_drew_reads_as_excess_even_if_unchanged(self) -> None:
        """Ensure the known bias: only the recording is smoothed, so a drawn corner scores high."""
        assert audit.audit_stroke(RIGHT_ANGLE, RIGHT_ANGLE)["excess"] > 0.0

    def test_a_kink_the_human_never_drew_is_a_positive_excess(self) -> None:
        """Ensure that a sharp corner replacing a gentle curve ranks as introduced bend."""
        row = audit.audit_stroke(ARC, RIGHT_ANGLE)
        assert row["excess"] > audit.KINK_EXCESS_DEG

    def test_rows_are_ranked_worst_first_and_skip_remarks(self) -> None:
        """Ensure that the worst excess is first and the _remarks key is ignored."""
        raw = {
            "_remarks": {"x": 1},
            "good": {"strokes": [{"d": ARC}]},
            "bad": {"strokes": [{"d": ARC}]},
        }
        processed = {
            "good": {"strokes": [{"d": ARC}]},
            "bad": {"strokes": [{"d": RIGHT_ANGLE}]},
        }
        rows = audit.audit_atoms(raw, processed)
        assert [r["atom"] for r in rows] == ["bad", "good"]
        assert rows[1]["unchanged"] is True and rows[0]["unchanged"] is False

    def test_a_changed_stroke_count_is_reported_not_measured(self) -> None:
        """Ensure that an atom whose stroke count differs is flagged instead of miscompared."""
        raw = {"a": {"strokes": [{"d": ARC}, {"d": STRAIGHT}]}}
        processed = {"a": {"strokes": [{"d": ARC}]}}
        rows = audit.audit_atoms(raw, processed)
        assert rows == [{"atom": "a", "stroke_count_mismatch": [2, 1]}]

    def test_an_unmeasurable_stroke_is_a_row_not_a_crash(self) -> None:
        """Ensure that one empty stroke is reported and the rest of the audit still runs."""
        raw = {"a": {"strokes": [{"d": ARC}, {"d": ""}]}, "b": {"strokes": [{"d": ARC}]}}
        processed = {"a": {"strokes": [{"d": ARC}, {"d": ""}]}, "b": {"strokes": [{"d": ARC}]}}
        rows = audit.audit_atoms(raw, processed)
        assert any(r.get("error") and r["stroke"] == 2 for r in rows)
        assert [r["atom"] for r in rows if "excess" in r] == ["a", "b"]

    def test_an_atom_missing_from_the_shipped_data_is_skipped(self) -> None:
        """Ensure that an atom with no shipped strokes produces no row."""
        assert audit.audit_atoms({"a": {"strokes": [{"d": ARC}]}}, {}) == []
