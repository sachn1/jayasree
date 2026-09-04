"""Registry of supported languages/scripts and their data-file conventions.

Phase 0 of `docs/LANGUAGE_ONBOARDING_AGENTS.md`: the single place that knows
how to go from a language name to its character-inventory module and its
committed data-file paths, so `tools/build_glyph_data.py`,
`tools/validate_data.py`, and `tools/process_strokes.py` don't each
reimplement (and risk disagreeing on) that mapping.

Adding a language means adding one `LanguageSpec` entry here plus its own
character-inventory module (e.g. `_chars_tamil.py`) - never editing another
language's entry or module. See `CONTRIBUTING.md`'s "Adding a new language".

A language module is expected to export whichever of these tuples its
script actually has - **all are optional except where noted**, since Indic
scripts differ structurally (Devanagari has no chillu-style bare-consonant
forms; not every script's compound vowel signs decompose the way
Malayalam's do; a script may have no "rare/archaic" category at all).
Nothing in this file, or in the tools that use it, assumes a script has
every category `_chars.py` (Malayalam's) happens to have:

    INDEPENDENT_VOWELS, RARE_VOWELS, CONSONANTS, RARE_CONSONANTS, CHILLU,
    NUMERALS, MATRAS, RARE_MATRAS, VIRAMA, ANUSVARA, VISARGA

This list isn't closed - it's exactly Malayalam's own categories, not a
fixed schema. Hindi's onboarding (`docs/languages/hi/`) already needed
three more that `tools/build_glyph_data.py` also recognizes if present:
`CANDRABINDU` (a second nasalization mark, phonemically distinct from
anusvara), `NUKTA` (a combining loanword-sound diacritic attached to
consonants, e.g. क + ़ = क़), and `NATIVE_PUNCTUATION` (script-owned
punctuation like Devanagari's danda - distinct from the shared-Latin
`UNIVERSAL_CHARS` in `index.js`, and gets a real recorded stroke). Expect
a future script to introduce further new category names the same way;
add support for a new one in `build_glyph_data.py` when a real profile
needs it, not speculatively ahead of one.

Only `INDEPENDENT_VOWELS`, `CONSONANTS`, `MATRAS`, and `VIRAMA` are
load-bearing for a script to be shapeable at all; see `char_tuple()` below
for how an absent category degrades to "no such characters" rather than an
error.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]

#: The one language whose committed files keep their original, unsuffixed
#: names (`glyph-data.json`, not `glyph-data.ml.json`) - required for
#: backward compatibility with the published npm package and the GitHub
#: Pages site, both of which fetch those exact URLs
#: (`js/src/index.js`'s `GLYPH_DATA_URL`/`STROKE_DATA_URL` default to them).
#: Every other language's files get `.{code}` inserted before the
#: extension. This is the *only* language ever entitled to the unsuffixed
#: names - a second language does not "take over" them.
PRIMARY_LANGUAGE = "malayalam"


@dataclass(frozen=True)
class LanguageSpec:
    """Everything the build/validate tooling needs to know about one language."""

    #: Short, stable identifier (ISO 639-1/3-ish) used as the data-file
    #: suffix and the `data(<code>): ...` commit scope (CONTRIBUTING.md).
    code: str
    #: Display name, e.g. "Malayalam".
    name: str
    #: Dotted module path exporting this language's character-inventory
    #: tuples (see this file's docstring for the expected/optional names).
    chars_module: str
    #: A single consonant whose standalone form renders as one glyph, used
    #: to shape matras/marks in isolation for `cli.py`'s `alphabet` command.
    carrier_consonant: str
    #: Path (repo-root-relative) to a bundled test-fixture font, if any.
    #: Only Malayalam has one today; every other language must pass
    #: `--font` explicitly until its own ghost font is chosen (see
    #: `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 2).
    default_font: str | None = None

    def chars(self) -> ModuleType:
        """Import and return this language's character-inventory module."""
        return import_module(self.chars_module)

    def resolved_default_font(self) -> Path | None:
        """Return `default_font` as an absolute path, or None if unset."""
        return (ROOT / self.default_font) if self.default_font else None


LANGUAGES: dict[str, LanguageSpec] = {
    "malayalam": LanguageSpec(
        code="ml",
        name="Malayalam",
        chars_module="jayasree._chars",
        carrier_consonant="ക",
        default_font="python/tests/fixtures/Manjari-Regular.ttf",
    ),
    # Planned, not yet onboarded - see docs/LANGUAGE_ONBOARDING_AGENTS.md's
    # target roster (Hindi, Tamil, Telugu, Kannada, Bengali, Sanskrit, one
    # at a time - and more beyond that). Add a real entry (plus its own
    # `_chars_<code>.py`) only once that pipeline's Agent 1/2/3 stages have
    # actually run for one of these; a bare registry entry with no
    # character-inventory module would just fail loudly on first use, so
    # there's no value in pre-registering them speculatively.
}


def get_language(name: str) -> LanguageSpec:
    """Look up a registered language by name.

    Parameters
    ----------
    name : str
        Registry key, e.g. ``"malayalam"``.

    Returns
    -------
    LanguageSpec
        The matching entry.

    Raises
    ------
    ValueError
        If `name` isn't registered - message lists what is.
    """
    try:
        return LANGUAGES[name]
    except KeyError:
        available = ", ".join(sorted(LANGUAGES)) or "(none registered)"
        raise ValueError(f"Unknown language {name!r}. Available: {available}.") from None


def char_tuple(module: ModuleType, attr: str) -> tuple[str, ...]:
    """Return `module.<attr>` if the language module defines it, else `()`.

    Lets a language module simply omit any category its script doesn't have
    (e.g. no `CHILLU`) without every caller needing its own
    `getattr(..., ())`.
    """
    return getattr(module, attr, ())


@dataclass(frozen=True)
class DataPaths:
    """A language's committed data-file paths under `js/src/`."""

    glyph_data: Path
    stroke_data_raw: Path
    stroke_data: Path
    snapshot: Path


def data_paths(lang: LanguageSpec) -> DataPaths:
    """Return the committed data-file paths for `lang`.

    Parameters
    ----------
    lang : LanguageSpec
        The language to compute paths for.

    Returns
    -------
    DataPaths
        `glyph_data`/`stroke_data_raw`/`stroke_data` under `js/src/`, and
        `snapshot` under `python/tests/snapshots/` - unsuffixed for
        `PRIMARY_LANGUAGE`, `.{code}`-suffixed for every other language.
    """
    is_primary = lang.code == LANGUAGES[PRIMARY_LANGUAGE].code
    suffix = "" if is_primary else f".{lang.code}"
    js_src = ROOT / "js" / "src"
    snapshots = ROOT / "python" / "tests" / "snapshots"
    return DataPaths(
        glyph_data=js_src / f"glyph-data{suffix}.json",
        stroke_data_raw=js_src / f"stroke-data{suffix}.raw.json",
        stroke_data=js_src / f"stroke-data{suffix}.json",
        snapshot=snapshots / f"stroke_data_raw_snapshot{suffix}.json",
    )
