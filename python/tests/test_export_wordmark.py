"""Tests for tools/export_wordmark.py - the animated wordmark SVG generator."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_wordmark  # noqa: E402

from jayasree import shape_word  # noqa: E402
from jayasree.languages import get_language  # noqa: E402

SVG = "{http://www.w3.org/2000/svg}"


def _trace() -> dict:
    """Return a tiny hand-made trace: two glyphs and one empty one (a space)."""
    return {
        "unitsPerEm": 1000,
        "ascent": 900,
        "descent": -400,
        "totalAdvance": 1500.0,
        "glyphs": [
            {"glyphName": "a", "cluster": 0, "d": "M0 0 L10 0 L10 -10 Z", "x": 0.0, "y": 0.0},
            {"glyphName": "sp", "cluster": 1, "d": "", "x": 700.0, "y": 0.0},
            {"glyphName": "b", "cluster": 2, "d": "M0 0 L20 0 L20 -20 Z", "x": 800.0, "y": 0.0},
        ],
    }


class TestBuildWordmarkSvg:
    """build_wordmark_svg: structure, colour and geometry of the generated SVG."""

    def test_is_well_formed_svg(self) -> None:
        """Ensure that the output parses as XML with an svg root."""
        root = ET.fromstring(export_wordmark.build_wordmark_svg(_trace()))
        assert root.tag == f"{SVG}svg"

    def test_viewbox_fits_the_ink_plus_a_tenth_of_the_em(self) -> None:
        """Ensure that the viewBox spans the advance and the ink's height, plus 10% em padding."""
        root = ET.fromstring(export_wordmark.build_wordmark_svg(_trace()))
        assert root.get("viewBox") == "-100.0 -120.0 1700.0 220.0"

    def test_empty_glyphs_are_skipped_and_the_rest_are_drawn_in_order(self) -> None:
        """Ensure that each inked glyph gets one fill and one pen path, and a space gets none."""
        root = ET.fromstring(export_wordmark.build_wordmark_svg(_trace()))
        fills = root.find(f"{SVG}g").findall(f"{SVG}path")
        pens = root.findall(f"{SVG}path")
        assert len(fills) == len(pens) == 2
        begins = [p.find(f"{SVG}animate").get("begin") for p in pens]
        assert begins == ["0.000s", "0.450s"]

    def test_outline_and_fill_share_one_colour_so_inner_contours_do_not_show(self) -> None:
        """Ensure that the pen stroke and the fill use the same colour."""
        root = ET.fromstring(export_wordmark.build_wordmark_svg(_trace(), "#123456"))
        assert root.find(f"{SVG}g").get("fill") == "#123456"
        assert {p.get("stroke") for p in root.findall(f"{SVG}path")} == {"#123456"}

    def test_fill_is_opaque(self) -> None:
        """Ensure that no fill-opacity is set (a translucent fill would show overlap seams)."""
        assert "fill-opacity" not in export_wordmark.build_wordmark_svg(_trace())


def test_hindi_wordmark_is_exported_from_its_native_name() -> None:
    """Ensure that Hindi's own spelling of the project name shapes to a non-empty wordmark."""
    lang = get_language("hindi")
    font = lang.resolved_default_font()
    assert font is not None
    svg = export_wordmark.build_wordmark_svg(shape_word(lang.native_name, font))
    root = ET.fromstring(svg)
    assert len(root.find(f"{SVG}g").findall(f"{SVG}path")) >= 3


def test_text_that_shapes_to_no_ink_is_a_clear_error() -> None:
    """Ensure that a trace with no visible glyphs raises a ValueError, not a min() traceback."""
    empty = {**_trace(), "glyphs": [{"glyphName": "sp", "cluster": 0, "d": "", "x": 0.0, "y": 0.0}]}
    with pytest.raises(ValueError, match="no visible glyphs"):
        export_wordmark.build_wordmark_svg(empty)


def test_main_writes_the_hindi_wordmark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that the command line writes a parseable SVG in the requested colour."""
    out = tmp_path / "w.svg"
    argv = ["export_wordmark.py", "--lang", "hindi", "--color", "#102030", "--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    export_wordmark.main()
    root = ET.fromstring(out.read_text(encoding="utf-8"))
    assert root.find(f"{SVG}g").get("fill") == "#102030"


def test_blank_word_exits_with_a_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that a word with no ink exits with a message instead of a traceback."""
    argv = [
        "export_wordmark.py",
        "--lang",
        "hindi",
        "--word",
        " ",
        "--output",
        str(tmp_path / "x.svg"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        export_wordmark.main()
    assert "no visible glyphs" in str(exc.value)


def test_demo_css_uses_the_same_colour_as_the_exported_hindi_wordmark() -> None:
    """Ensure that the live demo wordmark colour and the tool's default cannot drift apart."""
    css = (ROOT / "demo" / "demo.css").read_text(encoding="utf-8")
    assert f"--ms-ink-color: {export_wordmark.DEFAULT_COLOR}" in css
    svg = (ROOT / "demo" / "jayasree.hi.svg").read_text(encoding="utf-8")
    assert export_wordmark.DEFAULT_COLOR in svg
