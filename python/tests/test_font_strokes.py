"""Tests for tools/build_font_strokes.py: reading pen strokes from SVGs, building the font set."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_font_strokes as bfs  # noqa: E402

SVG = """<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g inkscape:groupmode="layer" transform="translate(0,100)">
    <g transform="translate(5,0)">
      <path style="fill:none;stroke:#000000;stroke-width:130" d="m 10,20 l 30,0"/>
      <path style="fill:#000000;stroke:none" d="m 0,0 l 50,50 z"/>
    </g>
  </g>
</svg>"""


def _first_point(d: str) -> tuple[float, float]:
    z = parse_path(d).start
    return z.real, z.imag


def test_parse_transform_composes_in_order() -> None:
    """Ensure that a translate then a scale combine as SVG applies them (left to right)."""
    assert bfs.parse_transform("translate(10,0) scale(2)") == (2.0, 0.0, 0.0, 2.0, 10.0, 0.0)


def test_parse_transform_of_nothing_is_the_identity() -> None:
    """Ensure that a missing transform leaves points where they are."""
    assert bfs.parse_transform(None) == bfs.IDENTITY


def test_parse_transform_rejects_what_it_cannot_apply() -> None:
    """Ensure that an unsupported transform is an error, not a silent mis-placement."""
    with pytest.raises(ValueError, match="rotate"):
        bfs.parse_transform("rotate(45)")


def test_path_d_applies_the_matrix_to_a_relative_path() -> None:
    """Ensure that a relative path is returned absolute and moved by the translate."""
    d = bfs.path_d("m 10,20 c 0,0 5,5 10,10", (1.0, 0.0, 0.0, 1.0, 100.0, 0.0))
    assert d.startswith("M 110.0 20.0 C")
    assert d.endswith("120.0 30.0")


def test_svg_strokes_keeps_pen_strokes_and_skips_outlines(tmp_path: Path) -> None:
    """Ensure that only the stroked, unfilled path is returned."""
    assert len(bfs.svg_strokes(_write(tmp_path, SVG))) == 1


def test_svg_strokes_puts_the_baseline_at_zero(tmp_path: Path) -> None:
    """Ensure that the layer's translate is taken out but an inner group's is kept."""
    (d,) = bfs.svg_strokes(_write(tmp_path, SVG))
    assert _first_point(d) == (15.0, 20.0)


def test_split_copies_separates_glyphs_drawn_side_by_side() -> None:
    """Ensure that strokes far apart in x are different copies, and touching ones are the same."""
    a, b, c = "M 0 0 L 100 0", "M 90 0 L 200 0", "M 2000 0 L 2100 0"
    assert bfs.split_copies([a, c, b]) == [[a, b], [c]]


def test_fit_to_ghost_centres_the_strokes_on_the_outline() -> None:
    """Ensure that a stroke's bounding box ends up centred on the glyph outline's."""
    ghost = [{"d": "M 0 0 L 100 0 L 100 100 L 0 100 Z", "x": 500.0, "y": 500.0}]
    (d,) = bfs.fit_to_ghost(["M 0 0 L 10 0"], ghost)
    x0, x1, y0, y1 = parse_path(d).bbox()
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == (550.0, 550.0)


def test_path_d_keeps_a_pen_lift_as_a_new_subpath() -> None:
    """Ensure that a second subpath is not joined to the first by a connecting curve."""
    d = bfs.path_d("M 0,0 L 10,0 M 50,50 L 60,50", bfs.IDENTITY)
    assert d.count("M") == 2


def test_path_d_rejects_an_arc() -> None:
    """Ensure that a segment type it cannot copy is an error, not a silently wrong stroke."""
    with pytest.raises(ValueError, match="Arc"):
        bfs.path_d("M 0,0 A 10,10 0 0 1 20,0", bfs.IDENTITY)


def test_svg_strokes_reads_plain_fill_and_stroke_attributes(tmp_path: Path) -> None:
    """Ensure that a pen stroke written with attributes, not a style, is found."""
    path = '<path fill="none" stroke="#000" d="M 0,0 L 5,5"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg">{path}</svg>'
    assert len(bfs.svg_strokes(_write(tmp_path, svg))) == 1


def test_parse_transform_reads_a_matrix_and_a_single_scale_argument() -> None:
    """Ensure that matrix(...) and scale(s) are understood."""
    assert bfs.parse_transform("matrix(1 0 0 1 3 4)") == (1.0, 0.0, 0.0, 1.0, 3.0, 4.0)
    assert bfs.parse_transform("scale(2)") == (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)


def test_pick_copy_chooses_the_copy_that_lies_on_the_ink() -> None:
    """Ensure that the copy staying inside the outline beats one running outside it, by a margin."""
    ghost = [{"d": "M 0 0 L 400 0 L 400 400 L 0 400 Z", "x": 0.0, "y": 0.0}]
    on_ink = ["M 100 200 L 300 200"]
    off_ink = ["M 0 200 L 3000 200"]  # centred, it still runs far outside the outline
    strokes, margin = bfs.pick_copy([off_ink, on_ink], ghost)
    assert parse_path(strokes[0]).bbox()[2] == pytest.approx(200.0, abs=1.0)
    assert margin > 0


def test_split_copies_groups_a_grid_of_copies_in_both_directions() -> None:
    """Ensure that copies stacked above one another are separate groups, not one."""
    top, bottom = "M 0 0 L 100 0", "M 0 1000 L 100 1000"
    assert bfs.split_copies([top, bottom]) == [[top], [bottom]]


def test_are_weights_needs_equal_counts_and_similar_sizes() -> None:
    """Ensure that only groups of the same size and stroke count are the same letter repeated."""
    small, same, big = ["M 0 0 L 100 0"], ["M 500 0 L 610 0"], ["M 0 900 L 400 900"]
    assert bfs.are_weights([small, same])
    assert not bfs.are_weights([small, big])
    assert not bfs.are_weights([small, small + same])


def test_reference_glyphs_drops_a_marks_placeholder_circle() -> None:
    """Ensure that a mark is placed on its content glyph, whichever side of the circle it is on."""
    circle, content = {"d": "circle"}, {"d": "content"}
    assert bfs.reference_glyphs([circle, content], {"prefix": []}) == [content]
    assert bfs.reference_glyphs([content, circle], {"prefix": [1]}) == [content]
    assert bfs.reference_glyphs([circle, content], None) == [circle, content]


def test_cluster_name_maps_a_legacy_chillu_to_its_atom() -> None:
    """Ensure that consonant + virama + ZWJ is named by the atomic chillu codepoint."""
    assert bfs.cluster_name("ന്‍") == "ൻ"


def test_build_assembles_each_letters_chosen_strokes_in_order() -> None:
    """Ensure that the set holds exactly the chosen strokes, from any option, in the order given."""
    candidates = {
        "ക": {"Manjari": ["M 0 0 L 1 1", "M 9 9 L 8 8"], "Chilanka": ["M 2 2 L 3 3"]},
        "ഗ": {"Manjari (part 2)": ["M 4 4 L 5 5"]},
    }
    built = bfs.build(
        candidates, {"ക": ["Manjari:2", "Chilanka:1"], "ഗ": ["Manjari (part 2):1"], "ന": []}
    )
    assert built == {
        "ക": {"strokes": [{"d": "M 9 9 L 8 8"}, {"d": "M 2 2 L 3 3"}]},
        "ഗ": {"strokes": [{"d": "M 4 4 L 5 5"}]},
    }


@pytest.mark.parametrize("bad", ["Manjari:3", "Nupuram:1", "Manjari:x", "nonsense"])
def test_build_rejects_a_stroke_that_does_not_exist(bad: str) -> None:
    """Ensure that a stale choice is an error, not a letter quietly built with a stroke missing."""
    with pytest.raises(ValueError, match="unknown stroke"):
        bfs.build({"ക": {"Manjari": ["M 0 0 L 1 1", "M 2 2 L 3 3"]}}, {"ക": [bad]})


def _write(folder: Path, text: str) -> Path:
    path = folder / "glyph.svg"
    path.write_text(text, encoding="utf-8")
    return path


def test_reverse_d_starts_where_the_path_ends() -> None:
    """Ensure that a reversed path starts at the old end and ends at the old start."""
    path = parse_path(bfs.reverse_d("M 0 0 C 10 0 20 10 30 30 L 40 40"))
    assert (path.start, path.end) == (40 + 40j, 0j)


def test_build_draws_a_stroke_marked_with_a_tilde_the_other_way_round() -> None:
    """Ensure that a trailing ~ on a chosen stroke reverses it, and no ~ leaves it as it is."""
    candidates = {"ക": {"Manjari": ["M 0 0 L 10 0"]}}
    built = bfs.build(candidates, {"ക": ["Manjari:1~"]})
    assert parse_path(built["ക"]["strokes"][0]["d"]).start == 10 + 0j
    assert bfs.build(candidates, {"ക": ["Manjari:1"]})["ക"]["strokes"][0]["d"] == "M 0 0 L 10 0"


def test_svg_strokes_keeps_an_open_path_that_is_filled_as_well_as_stroked(tmp_path: Path) -> None:
    """Ensure that a straight line saved with a fill is a pen stroke; a closed outline is not."""
    line = '<path style="fill:#000;stroke:#000;stroke-width:140" d="m 10,20 908,0"/>'
    outline = '<path style="fill:#000;stroke:#000;stroke-width:140" d="m 0,0 10,0 10,10 z"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg">{line}{outline}</svg>'
    assert len(bfs.svg_strokes(_write(tmp_path, svg))) == 1


def _field(ghost: list[dict]):  # noqa: ANN202 - a DistField; only the tests build one
    from jayasree.cleanup import ink

    return ink.make_field_winding(ghost)


def test_refine_placement_moves_strokes_that_miss_the_ink_onto_it() -> None:
    """Ensure that a stroke centred between two stacked letters is moved onto its own letter."""
    top = {"d": "M 0 0 L 300 0 L 300 100 L 0 100 Z", "x": 0.0, "y": 0.0}
    bottom = {"d": "M 0 600 L 300 600 L 300 700 L 0 700 Z", "x": 0.0, "y": 0.0}
    field = _field([top, bottom])
    stroke = ["M 20 350 L 280 350"]  # centred on the pair, so on neither bar
    (moved,) = bfs.refine_placement(stroke, field)
    y = parse_path(moved).start.imag
    assert 0 <= y <= 100 or 600 <= y <= 700


def test_refine_placement_leaves_well_placed_strokes_alone() -> None:
    """Ensure that strokes already on the ink are returned as they are."""
    ghost = [{"d": "M 0 0 L 300 0 L 300 100 L 0 100 Z", "x": 0.0, "y": 0.0}]
    stroke = ["M 20 50 L 280 50"]
    assert bfs.refine_placement(stroke, _field(ghost)) == stroke


def test_fit_width_puts_the_ink_where_the_outlines_edges_allow() -> None:
    """Ensure that strokes are stretched to the outline's width less half a stroke width a side."""
    ghost = [{"d": "M 0 0 L 1000 0 L 1000 100 L 0 100 Z", "x": 0.0, "y": 0.0}]
    (d,) = bfs.fit_width(["M 150 50 L 850 50"], ghost)
    x0, x1, _, _ = parse_path(d).bbox()
    assert (x0, x1) == pytest.approx((bfs.INK_FU / 2, 1000 - bfs.INK_FU / 2), abs=0.2)


def test_build_fits_only_letters_drawn_entirely_from_chilanka() -> None:
    """Ensure that width fitting changes a pure-Chilanka letter and leaves Manjari ones alone."""
    ghost = [{"d": "M 0 0 L 1000 0 L 1000 100 L 0 100 Z", "x": 0.0, "y": 0.0}]
    glyphs = {"clusters": {"ക": {"glyphs": ghost}, "ഗ": {"glyphs": ghost}}, "marks": {}}
    candidates = {
        "ക": {"Chilanka": ["M 150 50 L 850 50"]},
        "ഗ": {"Manjari": ["M 150 50 L 850 50"]},
    }
    built = bfs.build(candidates, {"ക": ["Chilanka:1"], "ഗ": ["Manjari:1"]}, glyphs)
    assert built["ഗ"]["strokes"][0]["d"] == "M 150 50 L 850 50"
    assert parse_path(built["ക"]["strokes"][0]["d"]).bbox()[0] == pytest.approx(
        bfs.INK_FU / 2, abs=0.2
    )


def _glyph(x: float) -> dict:
    return {"d": "M 0 0 L 10 10", "x": x, "y": 0.0}


GLYPH_DATA = {
    "clusters": {
        "a": {"glyphs": [_glyph(0.0)], "advance": 100.0},
        "b": {"glyphs": [_glyph(0.0)], "advance": 100.0},
        "ab": {"glyphs": [_glyph(0.0), _glyph(100.0)], "advance": 200.0},
    },
    "marks": {},
}


def test_bake_composes_a_cluster_from_the_chosen_letters_it_is_made_of() -> None:
    """Ensure that a cluster of two letters, each chosen, is written with both letters' strokes."""
    atoms = {"a": {"strokes": [{"d": "M 1 1 L 2 2"}]}, "b": {"strokes": [{"d": "M 3 3 L 4 4"}]}}
    full, missing = bfs.bake(GLYPH_DATA, atoms)
    assert missing == []
    assert len(full["ab"]["strokes"]) == 2


def test_bake_reports_the_clusters_a_missing_letter_makes_impossible() -> None:
    """Ensure that a letter with no chosen strokes leaves it and each cluster using it unwritten."""
    atoms = {"a": {"strokes": [{"d": "M 1 1 L 2 2"}]}}
    full, missing = bfs.bake(GLYPH_DATA, atoms)
    assert missing == ["ab", "b"]
    assert "ab" not in full


def test_mp_strokes_returns_only_the_open_centre_line_paths(tmp_path: Path) -> None:
    """Ensure that a Nupuram debug SVG yields its grey open paths, not outlines or grid lines."""
    grey = "stroke:rgb(80.000305%,80.000305%,80.000305%); fill: none;"
    centre = f'<path d="M10 20C30 40,50 60,70 80" style="{grey}"></path>'
    outline = '<path d="M0 0L10 0L10 10Z" style="fill: rgb(10%,37%,71%);stroke: none;"></path>'
    grid_style = "stroke:rgb(47.000122%,46.000671%,47.999573%); fill: none;"
    grid = f'<path d="M0 0L9 9" style="{grid_style}"></path>'
    path = tmp_path / "glyph.svg"
    path.write_text(f"<svg>{centre}{outline}{grid}</svg>", encoding="utf-8")
    assert len(bfs.mp_strokes(path)) == 1


def test_fit_box_scales_each_direction_to_the_outline() -> None:
    """Ensure that strokes on a smaller unit size are scaled to fill the outline both ways."""
    ghost = [{"d": "M 0 0 L 1000 0 L 1000 600 L 0 600 Z", "x": 0.0, "y": 0.0}]
    (d,) = bfs.fit_box(["M 100 100 L 500 400"], ghost)
    x0, x1, y0, y1 = parse_path(d).bbox()
    inset = bfs.INK_FU / 2
    assert (x0, x1, y0, y1) == pytest.approx((inset, 1000 - inset, inset, 600 - inset), abs=0.2)


def _paths(data: dict) -> set[str]:
    """Return every stroke path in a stroke-data file."""
    return {s["d"] for v in data.values() for s in (v["strokes"] if isinstance(v, dict) else v)}


def test_font_strokes_never_contain_handwriting() -> None:
    """Ensure that no stroke of the font-based set is one of the recorded handwriting strokes."""
    import json

    font = json.loads((ROOT / "js/src/stroke-data.font.json").read_text("utf-8"))
    hand = json.loads((ROOT / "js/src/stroke-data.json").read_text("utf-8"))
    assert not _paths(font) & _paths(hand)


def test_every_chosen_letter_is_in_the_font_data() -> None:
    """Ensure that each letter the owner chose strokes for is baked into the font-based set."""
    import json

    font = json.loads((ROOT / "js/src/stroke-data.font.json").read_text("utf-8"))
    chosen = json.loads((ROOT / "tools/font-stroke-choices.ml.json").read_text("utf-8"))
    assert [k for k in chosen if k not in font] == []
