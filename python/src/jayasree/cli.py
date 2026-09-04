"""CLI: shape word(s) or the full alphabet against a font, print JSON - see README.md."""

from __future__ import annotations

import argparse
import json
import sys

from .languages import char_tuple, get_language
from .strokes import shape_word


def _standalone_run(lang_name: str) -> str:
    """All of `lang_name`'s standalone characters, as a single string (one shaped run)."""
    chars = get_language(lang_name).chars()
    return "".join(
        char_tuple(chars, "INDEPENDENT_VOWELS")
        + char_tuple(chars, "RARE_VOWELS")
        + char_tuple(chars, "CONSONANTS")
        + char_tuple(chars, "RARE_CONSONANTS")
        + char_tuple(chars, "CHILLU")
        + char_tuple(chars, "NUMERALS")
    )


def _matra_syllables(lang_name: str) -> list[str]:
    """Each of `lang_name`'s matras/marks shaped with a carrier consonant.

    Shaping with a carrier (rather than alone) makes the shaper emit the
    actual dependent-vowel-sign glyph instead of a HarfBuzz placeholder
    circle. The recorder deduplicates by glyphName, so the carrier itself
    appears only once regardless of how many syllables use it.
    """
    lang = get_language(lang_name)
    chars = lang.chars()
    carrier = lang.carrier_consonant
    all_matras = char_tuple(chars, "MATRAS") + char_tuple(chars, "RARE_MATRAS")
    syllables = [carrier + m for m in all_matras]
    for mark_attr in ("ANUSVARA", "VISARGA", "VIRAMA"):
        mark = getattr(chars, mark_attr, None)
        if mark:
            syllables.append(carrier + mark)
    return syllables


def _cmd_shape(args: argparse.Namespace) -> int:
    """Shape one or more words and print a JSON array to stdout.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with ``font_path`` and ``words`` attributes.

    Returns
    -------
    int
        Exit code (0 = success, 1 = a word failed to shape).
    """
    results = []
    for word in args.words:
        try:
            trace = shape_word(word, args.font_path)
        except (ValueError, OSError) as exc:
            print(f"error shaping {word!r}: {exc}", file=sys.stderr)
            return 1
        results.append({"word": word, **trace})
    json.dump(results, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def _cmd_alphabet(args: argparse.Namespace) -> int:
    """Shape a language's full character inventory and print a JSON array.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with ``font_path`` and ``lang`` attributes.

    Returns
    -------
    int
        Exit code (0 = success, 1 = the standalone run failed to shape, or
        `lang` isn't registered).
    """
    try:
        standalone = _standalone_run(args.lang)
        matra_syllables = _matra_syllables(args.lang)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    results = []

    # All standalone characters shaped as one long string
    try:
        trace = shape_word(standalone, args.font_path)
        results.append({"word": "standalone", **trace})
    except (ValueError, OSError) as exc:
        print(f"error shaping standalone characters: {exc}", file=sys.stderr)
        return 1

    # Each matra syllable shaped individually so the vowel sign glyph is emitted
    for syllable in matra_syllables:
        try:
            trace = shape_word(syllable, args.font_path)
            results.append({"word": syllable, **trace})
        except (ValueError, OSError) as exc:
            print(f"warning: could not shape {syllable!r}: {exc}", file=sys.stderr)

    json.dump(results, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate sub-command.

    Parameters
    ----------
    argv : list[str] or None
        Argument list; defaults to ``sys.argv[1:]`` when ``None``.

    Returns
    -------
    int
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        prog="jayasree",
        description="Shape Indic-script text and print stroke-trace JSON.",
    )
    sub = parser.add_subparsers(dest="cmd")

    # ── shape (default) ──────────────────────────────────────────────────
    p_shape = sub.add_parser("shape", help="Shape one or more words (default)")
    p_shape.add_argument("font_path", help="Path to a .ttf/.otf font file")
    p_shape.add_argument("words", nargs="+", help="One or more words to shape")

    # ── alphabet ─────────────────────────────────────────────────────────
    p_alpha = sub.add_parser(
        "alphabet",
        help="Shape a language's full base alphabet - ideal input for the stroke recorder",
    )
    p_alpha.add_argument("font_path", help="Path to a .ttf/.otf font file")
    p_alpha.add_argument(
        "--lang",
        default="malayalam",
        help="Registry key from jayasree.languages.LANGUAGES (default: malayalam)",
    )

    # Backwards-compatible: no sub-command → treat all positional args as
    # font_path + words (old behaviour). Must happen *before* parse_args():
    # argparse's subparser positional matches (or rejects) the first token
    # immediately, so an unrecognised first token - a font path, in the old
    # calling convention - raises "invalid choice" and exits before any
    # after-the-fact fallback logic could run.
    raw = argv if argv is not None else sys.argv[1:]
    if not raw:
        parser.print_help()
        return 0
    if raw[0] not in ("shape", "alphabet", "-h", "--help"):
        raw = ["shape", *raw]

    args = parser.parse_args(raw)

    if args.cmd == "alphabet":
        return _cmd_alphabet(args)
    return _cmd_shape(args)
