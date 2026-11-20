"""Tests for jayasree.cleanup - rebuilding a recorded stroke from the font's own geometry.

Deliberately script-agnostic: the glyphs are synthetic bars, blobs and rings, not letterforms.
Cleanup works from any filled outline, so a new script should never need to touch this file.
"""

from __future__ import annotations

import hashlib
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import process_strokes  # noqa: E402

from jayasree import centering, geometry  # noqa: E402
from jayasree.cleanup import clean_stroke, clean_strokes  # noqa: E402
from jayasree.cleanup.fitting import (  # noqa: E402
    beziers_to_d,
    fit_polyline,
    line_bezier,
    resample,
    smooth_pinned,
    unit,
)
from jayasree.cleanup.ink import BLOCKED_COST, make_field_winding, min_cost_path  # noqa: E402
from jayasree.cleanup.primitives import (  # noqa: E402
    assemble_with_lines,
    axis_direction,
    classify_stroke,
    exact_line,
    manufacture_dot,
    manufacture_line,
    straight_runs,
)
from jayasree.cleanup.shape import (  # noqa: E402
    arc_beziers,
    bad_spans,
    circle_snap_fit,
    circular_runs,
    corner_fillets,
    fair_in_channel,
    fit_circle,
    font_corners,
    splice_knots,
    stem_split,
)

# A tall vertical bar: x in [0, 60], y in [-400, 0]; its centre line is x = 30.
BAR = {"d": "M0 0 L60 0 L60 -400 L0 -400 Z", "x": 0, "y": 0}
# A small isolated square (a dot of ink) centred on (30, -30).
BLOB = {"d": "M10 -10 L50 -10 L50 -50 L10 -50 Z", "x": 0, "y": 0}
# A square ring: outer square, with the inner square wound the other way, so it is a hole.
RING = {
    "d": "M0 0 L300 0 L300 -300 L0 -300 Z M100 -100 L100 -200 L200 -200 L200 -100 Z",
    "x": 0,
    "y": 0,
}


def _wobbly_vertical(x: float = 30.0, wobble: float = 6.0) -> str:
    """Return a hand-like vertical stroke down the bar's middle, with some wobble."""
    ys = np.linspace(-20, -380, 13)
    xs = x + wobble * np.sin(np.arange(13) * 1.7)
    return "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in zip(xs, ys, strict=True))


class TestFitting:
    """fitting: resampling, pinned smoothing and the Bezier fit."""

    def test_unit_scales_to_length_one_and_leaves_zero_alone(self) -> None:
        """Ensure that unit() normalises a vector and does not divide by zero."""
        assert np.allclose(unit(np.array([3.0, 4.0])), [0.6, 0.8])
        assert np.allclose(unit(np.zeros(2)), [0.0, 0.0])

    def test_resample_spaces_points_evenly_and_keeps_the_ends(self) -> None:
        """Ensure that resample() keeps both ends and spaces points about `step` apart."""
        pts = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 100.0]])
        out = resample(pts, 10.0)
        assert np.allclose(out[0], pts[0]) and np.allclose(out[-1], pts[-1])
        gaps = np.hypot(*np.diff(out, axis=0).T)
        assert gaps.max() < 11.5

    def test_smooth_pinned_keeps_both_ends_exactly(self) -> None:
        """Ensure that smoothing never moves the first or last point."""
        rng = np.random.default_rng(1)
        pts = np.column_stack([np.linspace(0, 300, 60), rng.normal(0, 5, 60)])
        out = smooth_pinned(pts, 20.0, 5.0)
        assert np.allclose(out[0], resample(pts, 5.0)[0]) and np.allclose(out[-1], pts[-1])
        assert np.std(np.diff(out[:, 1])) < np.std(np.diff(pts[:, 1]))

    def test_fit_polyline_stays_within_the_error_bound_with_few_segments(self) -> None:
        """Ensure that a quarter circle is fitted by a handful of cubics within the bound."""
        t = np.linspace(0, np.pi / 2, 80)
        arc = 200 * np.column_stack([np.cos(t), np.sin(t)])
        segs = fit_polyline(arc, 2.0)
        assert 1 <= len(segs) <= 4
        d = beziers_to_d([segs])
        fitted = geometry.sample_path(d, 400)
        gap = max(np.min(np.hypot(*(fitted - p).T)) for p in arc)
        assert gap < 2.5

    def test_beziers_to_d_writes_one_move_and_one_c_per_cubic(self) -> None:
        """Ensure that the serialised path starts with M and has a C per cubic."""
        c = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 1.0], [3.0, 1.0]])
        d = beziers_to_d([[c, c]])
        assert d.startswith("M 0.0 0.0") and d.count("C ") == 2


class TestMinCostPath:
    """ink.min_cost_path: the replacement for scikit-image's route_through_array."""

    def test_uniform_grid_takes_a_shortest_route(self) -> None:
        """Ensure that on equal costs the path has the minimum number of steps."""
        path = min_cost_path(np.ones((20, 20)), (2, 2), (2, 9))
        assert path[0] == (2, 2) and path[-1] == (2, 9) and len(path) == 8

    def test_path_goes_around_a_blocked_wall(self) -> None:
        """Ensure that blocked cells are avoided when a free route exists."""
        cost = np.ones((15, 15))
        cost[3:12, 7] = BLOCKED_COST
        path = min_cost_path(cost, (7, 2), (7, 12))
        assert (7, 7) not in path and all(cost[r, c] < BLOCKED_COST for r, c in path)

    def test_prefers_cheap_cells_over_a_shorter_expensive_route(self) -> None:
        """Ensure that the cheapest, not the shortest, route is taken."""
        cost = np.full((9, 9), 50.0)
        cost[1, :] = 1.0
        path = min_cost_path(cost, (1, 0), (1, 8))
        assert {r for r, _ in path} == {1}

    def test_a_diagonal_costs_the_square_root_of_two(self) -> None:
        """Ensure that a diagonal beats two axis steps (1.414 < 2)."""
        path = min_cost_path(np.ones((5, 5)), (0, 0), (1, 1))
        assert path == [(0, 0), (1, 1)]


class TestFieldWinding:
    """ink.make_field_winding: the ink is nonzero winding, so a counter stays empty."""

    def test_a_hole_is_empty_but_the_body_is_ink(self) -> None:
        """Ensure that the middle of a ring reads as no ink while its body reads as ink."""
        field = make_field_winding([RING])
        hole_r, hole_c = centering.fu_to_px(field, 150, -150)
        body_r, body_c = centering.fu_to_px(field, 50, -150)
        assert field.dist[int(hole_r), int(hole_c)] == 0
        assert field.dist[int(body_r), int(body_c)] > 0


class TestPrimitives:
    """primitives: dots, exact lines and straight runs."""

    def test_classify_stroke(self) -> None:
        """Ensure that tiny, straight and curved strokes are told apart."""
        tiny = geometry.sample_path("M 0 0 L 20 15", 40)
        straight = geometry.sample_path("M 0 0 L 0 300", 40)
        curved = geometry.sample_path("M 0 0 C 150 0 150 300 0 300", 80)
        assert [classify_stroke(p) for p in (tiny, straight, curved)] == ["dot", "line", "curve"]

    def test_axis_direction_snaps_only_near_an_axis(self) -> None:
        """Ensure that a near-vertical direction snaps to the axis and a diagonal does not."""
        assert np.allclose(axis_direction(np.array([3.0, 100.0])), [0.0, 1.0])
        assert axis_direction(np.array([100.0, 100.0])) is None

    def test_exact_line_becomes_exactly_vertical(self) -> None:
        """Ensure that a slightly tilted segment is pivoted about its midpoint onto the axis."""
        a, b = exact_line(np.array([0.0, 0.0]), np.array([4.0, 200.0]))
        assert a[0] == b[0] == 2.0 and np.isclose(b[1] - a[1], np.hypot(4.0, 200.0))

    def test_straight_runs_finds_a_long_straight_stretch_only(self) -> None:
        """Ensure that a straight stretch is found and a pure arc has none."""
        straight = np.column_stack([np.linspace(0, 300, 60), np.zeros(60)])
        t = np.linspace(0, np.pi, 80)
        arc = 150 * np.column_stack([np.cos(t), np.sin(t)])
        assert straight_runs(straight) == [(0, 59)]
        assert straight_runs(arc) == []

    def test_manufacture_line_is_exactly_vertical_on_the_stems_centre(self) -> None:
        """Ensure that a wobbly stem stroke becomes one exact vertical line down the middle."""
        field = make_field_winding([BAR])
        pts = geometry.sample_path(_wobbly_vertical(), 240)
        d = manufacture_line(pts, field)
        assert d is not None and d.count("L") == 1
        xs = [float(v) for v in d.replace("M", "").replace("L", "").split()[0::2]]
        assert xs[0] == xs[1] and abs(xs[0] - 30.0) < 4.0

    def test_manufacture_dot_lands_on_an_isolated_blob_and_ignores_a_letter(self) -> None:
        """Ensure that a dot goes on a small blob, and a tap inside a big letter is not a dot."""
        blob_field = make_field_winding([BLOB])
        d = manufacture_dot(np.array([[28.0, -33.0], [33.0, -28.0]]), blob_field)
        assert d is not None and d.startswith("M ")
        bar_field = make_field_winding([BAR])
        assert manufacture_dot(np.array([[28.0, -200.0], [33.0, -205.0]]), bar_field) is None


class TestShape:
    """shape: corners, fairing, spans and circles."""

    def test_fit_circle_recovers_centre_and_radius(self) -> None:
        """Ensure that a sampled arc gives back its centre and radius."""
        t = np.linspace(0, 2.0, 40)
        arc = np.array([50.0, -20.0]) + 120 * np.column_stack([np.cos(t), np.sin(t)])
        centre, radius, deviation = fit_circle(arc)
        assert np.allclose(centre, [50.0, -20.0], atol=0.01) and abs(radius - 120) < 0.01
        assert deviation < 0.01

    def test_circular_runs_detects_a_round_stretch_but_not_a_line(self) -> None:
        """Ensure that a half circle is one circular run and a straight line has none."""
        t = np.linspace(0, np.pi, 70)
        half = 150 * np.column_stack([np.cos(t), np.sin(t)])
        line = np.column_stack([np.linspace(0, 300, 70), np.zeros(70)])
        assert len(circular_runs(half)) == 1
        assert circular_runs(line) == []

    def test_arc_beziers_lie_on_the_circle(self) -> None:
        """Ensure that each arc piece starts and ends on the circle and spans at most 90 deg."""
        arcs = arc_beziers(np.array([10.0, 5.0]), 100.0, 0.3, 2.5)
        assert len(arcs) == 2
        for c in arcs:
            assert np.isclose(np.hypot(*(c[0] - [10.0, 5.0])), 100.0)
            assert np.isclose(np.hypot(*(c[3] - [10.0, 5.0])), 100.0)

    def test_font_corners_finds_a_sharp_turn(self) -> None:
        """Ensure that an L-shaped ridge has one corner, near the bend."""
        m = np.vstack(
            [
                np.column_stack([np.linspace(0, 120, 21), np.zeros(21)]),
                np.column_stack([np.full(20, 120.0), np.linspace(6, 120, 20)]),
            ]
        )
        corners = font_corners(m, np.full(len(m), 10.0))
        assert len(corners) == 1 and abs(corners[0] - 20) <= 2

    def test_bad_spans_is_empty_for_a_clean_ridge(self) -> None:
        """Ensure that a smooth ridge deep in the ink has no untrustworthy span."""
        m = np.column_stack([np.linspace(0, 300, 50), np.zeros(50)])
        assert bad_spans(m, np.full(50, 40.0)) == []

    def test_bad_spans_flags_a_ridge_that_leaves_the_ink(self) -> None:
        """Ensure that points with ~zero ink radius are flagged."""
        m = np.column_stack([np.linspace(0, 300, 50), np.zeros(50)])
        radius = np.full(50, 40.0)
        radius[20:30] = 0.0
        assert bad_spans(m, radius)

    def test_fair_in_channel_pins_the_ends_and_stays_in_the_channel(self) -> None:
        """Ensure that the faired curve keeps its ends and never leaves alpha * radius."""
        rng = np.random.default_rng(3)
        m = np.column_stack([np.linspace(0, 300, 50), rng.normal(0, 3, 50)])
        radius = np.full(50, 20.0)
        out = fair_in_channel(m, radius, alpha=0.45, jerk_w=4.0)
        assert np.allclose(out[0], m[0], atol=1e-3) and np.allclose(out[-1], m[-1], atol=1e-3)
        assert np.abs(out[:, 1] - m[:, 1]).max() <= 0.45 * 20.0 + 1e-3


class TestCleanStroke:
    """clean_stroke / clean_strokes: the whole method on synthetic glyphs."""

    def test_a_wobbly_stem_becomes_an_exact_line(self) -> None:
        """Ensure that a stem stroke is reported as a manufactured line."""
        d, kind = clean_stroke(_wobbly_vertical(), make_field_winding([BAR]))
        assert kind == "line" and d.count("L") == 1

    def test_a_squiggle_on_a_blob_becomes_a_dot(self) -> None:
        """Ensure that a tiny stroke on an isolated blob is manufactured as a dot."""
        d, kind = clean_stroke("M 25 -35 L 33 -28 L 27 -26", make_field_winding([BLOB]))
        assert kind == "dot" and d.startswith("M ")

    def test_a_stray_tap_inside_a_letter_is_kept_as_recorded(self) -> None:
        """Ensure that a tiny stroke inside a big letter is left alone and flagged."""
        raw = "M 25 -200 L 33 -205 L 27 -207"
        d, kind = clean_stroke(raw, make_field_winding([BAR]))
        assert (d, kind) == (raw, "stray_tap")

    def test_cleaning_is_deterministic(self) -> None:
        """Ensure that the same input gives byte-identical output every time."""
        raw = ["M 5 -20 C 60 -40 -20 -300 40 -380"]
        assert clean_strokes(raw, [BAR]) == clean_strokes(raw, [BAR])

    def test_one_cleaned_stroke_per_recorded_stroke_in_order(self) -> None:
        """Ensure that clean_strokes returns as many paths as it was given, in order."""
        raws = [_wobbly_vertical(25.0), _wobbly_vertical(35.0, 2.0)]
        out = clean_strokes(raws, [BAR])
        assert len(out) == 2 and all(d.startswith("M ") for d in out)
        assert out[0] != out[1] or raws[0] == raws[1]

    @pytest.mark.parametrize("bad", ["", "M 0 0"])
    def test_a_degenerate_stroke_raises_a_value_error(self, bad: str) -> None:
        """Ensure that a path with no length is a ValueError, which the pipeline falls back on."""
        with pytest.raises(ValueError, match="zero-size"):
            clean_stroke(bad, make_field_winding([BAR]))

    def test_a_stem_drawn_up_then_down_ends_in_exact_vertical_lines(self) -> None:
        """Ensure that an out-and-back stem becomes straight lines along the stem's axis."""
        el = {"d": "M0 0 L330 0 L330 -330 L270 -330 L270 -60 L0 -60 Z", "x": 0, "y": 0}
        wob = 3.0 * np.sin(np.arange(40) * 1.3)
        head = [(10 + 7.5 * k, -30.0) for k in range(40)]
        up = [(300.0 + wob[k] * 0.3, -30.0 - 7.3 * k) for k in range(40)]
        down = [(300.0 - wob[k] * 0.3, -300.0 + 6.8 * k) for k in range(40)]
        raw = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in [*head, *up, *down])
        d, kind = clean_stroke(raw, make_field_winding([el]))
        pts = geometry.sample_path(d, 400)
        stem = pts[pts[:, 1] < -200]  # above the rounded corner into the stem
        assert kind == "curve" and len(stem) > 20
        assert np.abs(stem[:, 0] - stem[:, 0].mean()).max() < 1.5


class TestPipelineWiring:
    """process_strokes: cleanup is Hindi-only, whatever the arguments say."""

    GLYPH_DATA: ClassVar[dict] = {"clusters": {"A": {"glyphs": [BAR], "advance": 60}}, "marks": {}}
    ENTRY: ClassVar[dict] = {"strokes": [{"d": _wobbly_vertical()}]}

    def _run(self, lang_code: str) -> list[dict]:
        """Process the one synthetic cluster as the given language."""
        args = Namespace(center=True, smooth=True, straighten=True)
        return process_strokes._process_cluster_strokes(
            "A", self.ENTRY, self.GLYPH_DATA, args, lang_code
        )

    def test_hindi_uses_the_cleaned_strokes(self) -> None:
        """Ensure that Hindi returns exactly what clean_strokes produces."""
        expected = clean_strokes([self.ENTRY["strokes"][0]["d"]], [BAR])
        assert self._run("hi") == [{"d": expected[0]}]

    def test_malayalam_is_never_cleaned(self) -> None:
        """Ensure that a non-Hindi language gets the ordinary stages, not the cleanup."""
        cleaned = [{"d": clean_strokes([self.ENTRY["strokes"][0]["d"]], [BAR])[0]}]
        assert self._run("ml") != cleaned

    def test_hindi_half_form_without_a_cluster_entry_is_cleaned_against_its_ghost(self) -> None:
        """Ensure that a trigger atom known only by `contextualForms` is cleaned, not left raw."""
        glyph_data = {
            "clusters": {},
            "marks": {},
            "contextualForms": {
                "A": {"role": "halfForm", "ghost": {"glyphs": [BAR], "advance": 60}}
            },
        }
        args = Namespace(center=True, smooth=True, straighten=True)
        got = process_strokes._process_cluster_strokes("A", self.ENTRY, glyph_data, args, "hi")
        expected = clean_strokes([self.ENTRY["strokes"][0]["d"]], [BAR])
        assert got == [{"d": expected[0]}]

    def test_malayalam_ignores_contextual_form_ghosts(self) -> None:
        """Ensure that the ghost fallback never applies to a non-Hindi language."""
        glyph_data = {
            "clusters": {},
            "contextualForms": {
                "A": {"role": "halfForm", "ghost": {"glyphs": [BAR], "advance": 60}}
            },
        }
        args = Namespace(center=True, smooth=True, straighten=True)
        got = process_strokes._process_cluster_strokes("A", self.ENTRY, glyph_data, args, "ml")
        cleaned = [{"d": clean_strokes([self.ENTRY["strokes"][0]["d"]], [BAR])[0]}]
        assert got != cleaned


ATOM_BUCKETS = 24


def _in_sample(atom: str) -> bool:
    """Whether `atom` is one of the sampled Hindi atoms (chosen by a hash of its name)."""
    return int(hashlib.sha1(atom.encode("utf-8")).hexdigest(), 16) % ATOM_BUCKETS == 0


def test_committed_hindi_strokes_are_what_the_cleanup_produces() -> None:
    """Ensure that a sample of Hindi atoms regenerates byte-for-byte to the committed strokes.

    The data is generated (``make process-strokes PROJECT_LANG=hindi``), never hand-edited; this
    fails if the cleanup code changes without the data being regenerated, or the reverse. The
    sample is chosen by atom name, so adding atoms elsewhere does not reshuffle it.
    """
    src = ROOT / "js" / "src"
    glyph_data = json.loads((src / "glyph-data.hi.json").read_text(encoding="utf-8"))
    raw = json.loads((src / "stroke-data.hi.raw.json").read_text(encoding="utf-8"))
    committed = json.loads((src / "stroke-data.hi.json").read_text(encoding="utf-8"))
    # Half-form / reph trigger atoms have no `clusters` entry; they are cleaned against their
    # `contextualForms` ghost, so they belong in the sample too.
    known = {**glyph_data["clusters"], **glyph_data.get("contextualForms", {})}
    sample = [a for a in sorted(raw) if a != "_remarks" and a in known]
    sample = [a for a in sample if _in_sample(a)]
    assert len(sample) >= 4, "the sample is too small to mean anything"
    args = Namespace(center=True, smooth=True, straighten=True)
    stale = []
    for atom in sample:
        strokes = process_strokes._process_cluster_strokes(atom, raw[atom], glyph_data, args, "hi")
        if atom in process_strokes._HI_STEM_LAST_ATOMS:
            strokes = process_strokes._hi_stem_last(strokes)
        if strokes != committed[atom]["strokes"]:
            stale.append(atom)
    assert stale == [], "committed Hindi strokes are out of date: run make process-strokes"


class TestShapeBranches:
    """Direct tests for shape and primitive paths the end-to-end tests only touch by accident."""

    def test_corner_fillets_round_a_corner_the_human_cut(self) -> None:
        """Ensure that a sharp ridge corner the recorded path cut gets a bridging cubic."""
        m = np.vstack(
            [
                np.column_stack([np.linspace(0, 120, 21), np.zeros(21)]),
                np.column_stack([np.full(20, 120.0), np.linspace(6, 120, 20)]),
            ]
        )
        pts = np.array([[0, 0], [60, 0], [100, 5], [110, 10], [117, 17], [120, 60], [120, 120.0]])
        out = corner_fillets(m, [20], pts, np.full(len(m), 10.0))
        assert list(out) == [20]
        trim, bez = out[20]
        assert trim >= 2 and np.allclose(bez[0], m[20 - trim]) and np.allclose(bez[3], m[20 + trim])

    def test_corner_fillets_leave_a_corner_the_human_kept_sharp(self) -> None:
        """Ensure that a corner the recorded path reaches exactly is not rounded."""
        m = np.vstack(
            [
                np.column_stack([np.linspace(0, 120, 21), np.zeros(21)]),
                np.column_stack([np.full(20, 120.0), np.linspace(6, 120, 20)]),
            ]
        )
        sharp = np.array([[0, 0], [60, 0], [120, 0], [120, 60], [120, 120.0]])
        assert corner_fillets(m, [20], sharp, np.full(len(m), 10.0)) == {}

    def test_splice_knots_restores_the_humans_curl_where_the_ridge_failed(self) -> None:
        """Ensure that a span with no ink radius is replaced by the human's own bulge."""
        m = np.column_stack([np.arange(60) * 6.0, np.zeros(60)])
        radius = np.full(60, 40.0)
        radius[25:36] = 0.0
        xs = np.arange(60) * 6.0
        ys = np.where((xs > 150) & (xs < 210), -50 * np.sin(np.pi * (xs - 150) / 60), 0.0)
        out, knots = splice_knots(m, np.column_stack([xs, ys]), radius)
        assert knots and np.abs(out[:, 1]).max() > 25

    def test_circle_snap_fit_makes_arcs_for_a_round_stretch_only(self) -> None:
        """Ensure that a half circle is fitted with arcs and a straight line is declined."""
        t = np.linspace(0, np.pi, 90)
        half = 150 * np.column_stack([np.cos(t), np.sin(t)])
        segs = circle_snap_fit(half, 2.0)
        assert segs is not None and len(segs) >= 2
        assert (
            circle_snap_fit(np.column_stack([np.linspace(0, 300, 90), np.zeros(90)]), 2.0) is None
        )

    def test_assemble_with_lines_keeps_the_line_exact_and_joins_the_curve_to_it(self) -> None:
        """Ensure that a pinned run is emitted as its exact line, with a fitted curve before it."""
        c = np.column_stack([np.arange(60) * 6.0, np.zeros(60)])
        c[:20, 1] = -np.linspace(40, 0, 20)
        a, b = c[20].copy(), c[59].copy()
        segs = assemble_with_lines(c, 2.0, [(20, 59, a, b)])
        assert len(segs) >= 2 and np.allclose(segs[-1], line_bezier(a, b))
        assert np.allclose(segs[0][0], c[0])
        assert len(assemble_with_lines(c, 2.0, [])) >= 1

    def test_stem_split_finds_a_stem_drawn_up_then_down(self) -> None:
        """Ensure that a head then an out-and-back stem is split into head and stem points."""
        head = np.column_stack([np.arange(51) * 6.0, np.zeros(51)])
        up = np.column_stack([np.full(50, 300.0), -np.arange(1, 51) * 6.0])
        m = np.vstack([head, up, up[::-1][1:]])
        rng = np.random.default_rng(5)
        pts = m[::2] + rng.normal(0, 1.5, m[::2].shape)
        split = stem_split(m, pts, np.full(len(m), 30.0))
        assert split is not None
        _head, (p_junction, p_tip, p_end), proj = split
        assert abs(p_junction[0] - p_tip[0]) < 1 and abs(p_tip[0] - p_end[0]) < 1
        assert np.allclose(proj(np.array([310.0, -100.0])), [p_tip[0], -100.0], atol=1.0)

    def test_stem_split_declines_a_plain_curve(self) -> None:
        """Ensure that a stroke with no out-and-back is not split."""
        m = np.column_stack([np.arange(80) * 6.0, 40 * np.sin(np.arange(80) / 12)])
        assert stem_split(m, m[::2], np.full(80, 30.0)) is None


class TestFailureHandling:
    """Explicit errors, and a failed cleanup that is recorded instead of hidden."""

    def test_an_all_blocked_grid_is_a_value_error(self) -> None:
        """Ensure that there being no traversable cell is a clear ValueError."""
        with pytest.raises(ValueError, match="blocked"):
            min_cost_path(np.full((5, 5), BLOCKED_COST), (0, 0), (4, 4))

    def test_a_path_from_a_cell_to_itself_is_that_cell(self) -> None:
        """Ensure that start == end gives a one-cell path."""
        assert min_cost_path(np.ones((5, 5)), (2, 2), (2, 2)) == [(2, 2)]

    def test_glyphs_with_no_ink_are_a_value_error(self) -> None:
        """Ensure that an empty glyph list is a clear ValueError, not a numpy reduction error."""
        with pytest.raises(ValueError, match="no ink"):
            make_field_winding([])

    def test_a_failed_cleanup_falls_back_and_is_recorded(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Ensure that a cluster whose cleanup raises uses the stages and is listed as a failure."""

        def boom(raw_ds: list[str], glyphs: list[dict]) -> list[str]:
            raise ValueError("singular")

        monkeypatch.setattr(process_strokes, "clean_strokes", boom)
        process_strokes._CLEANUP_FAILURES.clear()
        wiring = TestPipelineWiring()
        assert wiring._run("hi") == wiring._run("ml")
        assert process_strokes._CLEANUP_FAILURES == ["A"]
        assert "cleanup failed for 'A'" in capsys.readouterr().err
        process_strokes._CLEANUP_FAILURES.clear()

    def test_a_programming_error_is_not_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure that a TypeError, which is a bug and not bad input, still stops the run."""

        def bug(raw_ds: list[str], glyphs: list[dict]) -> list[str]:
            raise TypeError("a bug")

        monkeypatch.setattr(process_strokes, "clean_strokes", bug)
        with pytest.raises(TypeError):
            TestPipelineWiring()._run("hi")
