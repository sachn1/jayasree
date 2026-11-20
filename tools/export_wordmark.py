#!/usr/bin/env python3
"""Export a language's animated wordmark (the project's name in its script) as an SVG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

from svgpathtools import parse_path

from jayasree import StrokeTrace, shape_word
from jayasree.languages import get_language

#: The command-line help (the module docstring stays one line, per CONTRIBUTING).
_HELP = """Export a language's animated wordmark (the project's name in its script) as an SVG.

The result is in the spirit of the Malayalam wordmark on the landing page (which was exported by
hand and is not produced by this tool): a pen outline of each
glyph is drawn first, then the solid shape is revealed from left to right. Outline and fill share
one colour, so the overlapping inner contours of a thick font do not show as seams.

The word is the language's ``native_name`` (``jayasree.languages``), shaped with its bundled ghost
font; ``--word`` and ``--font`` override both. Example::

    cd python && poetry run python ../tools/export_wordmark.py --lang hindi \\
        --output ../demo/jayasree.hi.svg"""

#: Padding at the sides of the word, as a fraction of the em (the Malayalam wordmark uses 10%).
PADDING_EM = 0.1
#: How the ink is framed vertically, measured from the Malayalam wordmark (demo/jayasree.svg) so
#: that two wordmarks shown at the same height line up: the ink fills this fraction of the image's
#: height, and its centre sits this far down it (0 = top, 1 = bottom).
INK_FILL = 0.68
INK_CENTRE = 0.446
#: Pen-outline width as a fraction of the em, and the pace of the animation, in seconds.
PEN_WIDTH_EM = 0.02
PEN_SECONDS_PER_GLYPH = 0.45
REVEAL_SECONDS = 0.65
DEFAULT_COLOR = "#e06c75"


def build_wordmark_svg(trace: StrokeTrace, color: str = DEFAULT_COLOR) -> str:
    """Return the animated wordmark SVG for one shaped word.

    Parameters
    ----------
    trace : StrokeTrace
        ``shape_word``'s result for the wordmark's text.
    color : str
        One CSS colour used for both the pen outline and the solid fill.

    Returns
    -------
    str
        A complete, self-contained SVG document (SMIL-animated, no script).
    """
    em = trace["unitsPerEm"]
    pad = em * PADDING_EM
    glyphs = [g for g in trace["glyphs"] if g["d"]]
    if not glyphs:
        raise ValueError("the text shaped to no visible glyphs; nothing to draw")
    # Frame the vertical range around the ink, not the font's ascent/descent (a word without
    # descenders would float above a band of empty space), and in the same proportions as the
    # Malayalam wordmark so the two sit level, at the same scale, side by side.
    ink = [parse_path(g["d"]).bbox() for g in glyphs]
    top = min(b[2] + g["y"] for b, g in zip(ink, glyphs, strict=True))
    bottom = max(b[3] + g["y"] for b, g in zip(ink, glyphs, strict=True))
    height = (bottom - top) / INK_FILL
    x0, y0 = -pad, (top + bottom) / 2 - INK_CENTRE * height
    width = trace["totalAdvance"] + 2 * pad
    pen_done = len(glyphs) * PEN_SECONDS_PER_GLYPH

    fills = "\n".join(
        f'    <path d="{g["d"]}" transform="translate({g["x"]:.1f},{g["y"]:.1f})"/>' for g in glyphs
    )
    pens = "\n".join(
        f'  <path d="{g["d"]}" transform="translate({g["x"]:.1f},{g["y"]:.1f})" pathLength="1"\n'
        f'        fill="none" stroke="{color}" stroke-width="{em * PEN_WIDTH_EM:.1f}"\n'
        f'        stroke-linecap="round" stroke-linejoin="round"\n'
        f'        stroke-dasharray="1 1" stroke-dashoffset="1">\n'
        f'    <animate attributeName="stroke-dashoffset" from="1" to="0"\n'
        f'      begin="{i * PEN_SECONDS_PER_GLYPH:.3f}s" dur="{PEN_SECONDS_PER_GLYPH:.3f}s"'
        f' fill="freeze" calcMode="linear"/>\n'
        f"  </path>"
        for i, g in enumerate(glyphs)
    )
    # The clip id is the same in every exported wordmark, so these are meant to be loaded as <img>
    # (each gets its own document); inlining two on one page would make the ids collide.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{x0:.1f} {y0:.1f} {width:.1f} {height:.1f}">\n'
        f"  <defs>\n"
        f'    <clipPath id="reveal-clip">\n'
        f'      <rect x="{x0:.1f}" y="{y0:.1f}" width="0" height="{height:.1f}">\n'
        f'        <animate attributeName="width" begin="{pen_done:.3f}s" dur="{REVEAL_SECONDS}s"\n'
        f'          fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.33 1 0.68 1"\n'
        f'          values="0;{width:.1f}"/>\n'
        f"      </rect>\n"
        f"    </clipPath>\n"
        f"  </defs>\n"
        f'  <g clip-path="url(#reveal-clip)" fill="{color}">\n{fills}\n  </g>\n'
        f"{pens}\n"
        f"</svg>\n"
    )


def main() -> None:
    """Write the wordmark SVG for `--lang` to `--output`."""
    parser = argparse.ArgumentParser(description=_HELP.split("\n\n")[0])
    parser.add_argument("--lang", default="malayalam", help="Registry key (default: malayalam).")
    parser.add_argument("--word", help="Text to export (default: the language's native name).")
    parser.add_argument(
        "--font", type=Path, help="Font file (default: the language's bundled one)."
    )
    parser.add_argument(
        "--color", default=DEFAULT_COLOR, help=f"CSS colour (default {DEFAULT_COLOR})."
    )
    parser.add_argument("--output", type=Path, required=True, help="SVG file to write.")
    args = parser.parse_args()

    lang = get_language(args.lang)
    word = args.word or lang.native_name
    font = args.font or lang.resolved_default_font()
    if not word or font is None:
        sys.exit(f"{lang.name} has no native name or bundled font; pass --word and --font.")
    try:
        svg = build_wordmark_svg(shape_word(word, font), args.color)
    except ValueError as exc:
        sys.exit(f"{word!r}: {exc}")
    args.output.write_text(svg, encoding="utf-8")
    print(f"Wrote {args.output} ({word!r}, {lang.name})")


if __name__ == "__main__":
    main()
