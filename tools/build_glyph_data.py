#!/usr/bin/env python3
"""Pre-compute SVG glyph paths for a language's cluster inventory and write glyph-data.json.

Language-parametrized (Phase 0 of docs/LANGUAGE_ONBOARDING_AGENTS.md) via
`--lang`, defaulting to Malayalam - the only language onboarded so far.
Malayalam-specific quirks (subjoined-conjunct marks, the split compound
vowels, the two hand-curated extra ghosts) are gated behind `lang.code ==
"ml"` rather than assumed for every script - a new language's equivalent
quirks get discovered by that pipeline's Agent 1/2 and added as their own
gated block, not inherited from Malayalam's. Hindi's own quirks, gated
behind `lang.code == "hi"`: `्र` (rakaar/vattu) is recorded and composed
generically exactly like Malayalam's ്ര (see docs/languages/hi/
font-report.md); nukta's encoding duality (precomposed U+0958-095E vs.
decomposed base+U+093C) is normalized via `legacyEncodings`, the same
mechanism as Malayalam's chillu spelling; and half-forms/reph (see
`_build_contextual_forms()` below) get a `contextualForms` table once
`docs/languages/hi/labeling-worklist.md`'s "headline finding" showed
neither fits the mark-recipe model rakaar/nukta reuse - see
`docs/languages/hi/composition-primitives-report.md` for the verification
behind that table's design.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

from jayasree import shape_word  # noqa: E402
from jayasree.languages import (  # noqa: E402
    LanguageSpec,
    char_tuple,
    data_paths,
    get_language,
)

#: Compound vowel signs with a canonical (or, for ai, font-specific) split
#: into simpler marks - see js/src/index.js's SPLIT_VOWEL_PARTS. These never
#: need their own recorded stroke or standalone ghost; they're composed from
#: their parts at runtime instead. Malayalam-specific: which (if any) of a
#: new script's compound vowel signs decompose this way is a finding for
#: that script's own onboarding, not something to assume here.
_ML_SPLIT_VOWELS = ("ൊ", "ോ", "ൌ")  # ൊ ോ ൌ

#: Same data as _ML_SPLIT_VOWELS above, but as the actual decomposition
#: recipe (which simpler marks each one is built from, in application
#: order) rather than just the set of which marks need one. Written into
#: glyph-data.json as `splitVowelParts` so js/src/index.js's runtime
#: composer doesn't need this hardcoded - a language with no split marks at
#: all (most of them) simply gets an absent/empty key, and none of this
#: data is ever loaded into memory for that language's session. See
#: js/src/index.js's `_internal.applySequentialMarkStrokes`.
_ML_SPLIT_VOWEL_PARTS: dict[str, list[str]] = {
    "ൊ": ["െ", "ാ"],
    "ോ": ["േ", "ാ"],
    "ൌ": ["െ", "ൗ"],
}

#: Legacy 3-codepoint chillu spelling (consonant + virama + ZWJ) -> its
#: atomic Unicode 5.1+ codepoint, ordered to match CHILLU's own tuple order
#: (ൻർൽൾൺൿ <-> base consonants നരലളണക). Written into glyph-data.json as
#: `legacyEncodings` for the same reason as _ML_SPLIT_VOWEL_PARTS above -
#: see js/src/index.js's `_internal.normalizeChillus` and
#: docs/ARCHITECTURE.md's "Chillu letters".
_ML_VIRAMA_ZWJ = "്‍"  # virama + zero-width joiner - see the docstring above
_ML_LEGACY_CHILLU: dict[str, str] = {
    "ന" + _ML_VIRAMA_ZWJ: "ൻ",
    "ര" + _ML_VIRAMA_ZWJ: "ർ",
    "ല" + _ML_VIRAMA_ZWJ: "ൽ",
    "ള" + _ML_VIRAMA_ZWJ: "ൾ",
    "ണ" + _ML_VIRAMA_ZWJ: "ൺ",
    "ക" + _ML_VIRAMA_ZWJ: "ൿ",
}

#: Hindi's own encoding-duality case (docs/languages/hi/profile.md's
#: "Encoding duality" section, direct parallel to _ML_LEGACY_CHILLU above):
#: every one of these 7 nukta consonants has a real Unicode *canonical*
#: NFD decomposition into base-consonant + U+093C (verified directly via
#: `unicodedata.decomposition()` while building this table - this
#: corrects profile.md's own hedge that "some... are not canonical-
#: equivalent to their decomposed sequence"; all 7 actually are). Real text
#: mixes both spellings unpredictably, and this font shapes both to the
#: exact same single fused glyph (verified via HarfBuzz), so - same as
#: chillu - one recorded atom (the precomposed codepoint, kept in the
#: standard CONSONANTS set) covers both spellings once the decomposed one
#: normalizes to it here.
# Precomposed codepoints written as chr(0x...) rather than literal
# characters - a literal precomposed nukta letter in source text is
# visually indistinguishable from (and too easy for an editor/tool to
# silently NFC/NFD-normalize into) its own decomposed form, which would
# make the *values* below equal to the *keys*, silently turning this table
# into a no-op. chr() sidesteps that entirely.
_HI_NUKTA_BASE = "\u0915\u0916\u0917\u091c\u0921\u0922\u092b"  # क ख ग ज ड ढ फ
_HI_NUKTA_PRECOMPOSED = "\u0958\u0959\u095a\u095b\u095c\u095d\u095e"  # क़ ख़ ग़ ज़ ड़ ढ़ फ़
_HI_NUKTA_MARK = "\u093c"  # ़
_HI_NUKTA_CONSONANTS: dict[str, str] = {
    base + _HI_NUKTA_MARK: precomposed
    for base, precomposed in zip(_HI_NUKTA_BASE, _HI_NUKTA_PRECOMPOSED, strict=True)
}


def _standalone_inputs(lang: LanguageSpec, chars: object) -> list[str]:
    """Single-codepoint clusters: letters, digits, and standalone diacritics."""
    letters = (
        "".join(char_tuple(chars, "INDEPENDENT_VOWELS"))
        + "".join(char_tuple(chars, "RARE_VOWELS"))
        + "".join(char_tuple(chars, "CONSONANTS"))
        + "".join(char_tuple(chars, "RARE_CONSONANTS"))
        + "".join(char_tuple(chars, "CHILLU"))
        + "".join(char_tuple(chars, "NUMERALS"))
        # Script-owned punctuation (e.g. Devanagari's danda/double-danda) -
        # unlike UNIVERSAL_CHARS (Latin, shared across every script), this
        # is part of the script's own letterforms and gets a real ghost +
        # eventual recorded stroke, found via Hindi's onboarding profile
        # (docs/languages/hi/profile.md's "Native punctuation" section).
        + "".join(char_tuple(chars, "NATIVE_PUNCTUATION"))
        # Standalone marks with no closer-fitting category (e.g.
        # Devanagari's avagraha/Om) - found the same way NATIVE_PUNCTUATION
        # was, via Hindi's onboarding profile.
        + "".join(char_tuple(chars, "RARE_MARKS"))
    )
    inputs = list(letters)

    anusvara = char_tuple(chars, "ANUSVARA")
    visarga = char_tuple(chars, "VISARGA")
    au_length_mark = getattr(chars, "AU_LENGTH_MARK", None)
    # Candrabindu (Devanagari's alternate nasalization mark, phonemically
    # distinct from anusvara - see docs/languages/hi/profile.md) is the
    # same kind of always-follows-a-vowel mark as anusvara/visarga.
    candrabindu = char_tuple(chars, "CANDRABINDU")

    # These all appear after any cluster (including conjuncts), so they
    # need their own glyph-data entries.
    if isinstance(anusvara, str):
        inputs.append(anusvara)
    if isinstance(visarga, str):
        inputs.append(visarga)
    if isinstance(candrabindu, str):
        inputs.append(candrabindu)
    if au_length_mark:
        inputs.append(au_length_mark)

    virama = getattr(chars, "VIRAMA", None)
    matras = char_tuple(chars, "MATRAS")
    rare_matras = char_tuple(chars, "RARE_MATRAS")
    # Nukta (Devanagari's loanword-sound diacritic, e.g. क + ़ = क़) is a
    # combining mark attached directly to a consonant, the same shape of
    # problem virama is - found via Hindi's onboarding profile.
    nukta = getattr(chars, "NUKTA", None)

    # Virama/nukta and matras - give the recorder a real dotted-circle
    # ghost to trace over rather than recording these blind via the
    # recorder's custom-cluster field. Malayalam's split vowels are
    # excluded: they compose from simpler marks already covered here
    # instead of needing their own recorded stroke.
    if virama:
        inputs.append(virama)
    if nukta:
        inputs.append(nukta)
    split_vowels = _ML_SPLIT_VOWELS if lang.code == "ml" else ()
    inputs += [m for m in matras + rare_matras if m not in split_vowels]

    if lang.code == "ml":
        chillu = char_tuple(chars, "CHILLU")
        if virama and chillu:
            # ്ര (subjoined ra) - give the recorder a real reference ghost,
            # same reasoning as above, extended to a 2-codepoint mark.
            inputs.append(virama + "ര")
            # ൻറ (chillu-n + റ) - the one real exception to "chillu is
            # always word-final": the traditional spelling of the
            # -nte/-nre possessive suffix. See git history / CHANGELOG for
            # the full derivation (verified against real HarfBuzz output:
            # റ takes a distinct contextual glyph here).
            inputs.append(chillu[0] + "റ")

    if lang.code == "hi" and virama:
        # ्र (rakaar/vattu - र as a non-first conjunct member) - direct
        # Devanagari analogue of Malayalam's ്ര above: an exhaustive
        # 33x33 sweep (docs/languages/hi/font-report.md, reconfirmed
        # directly against this font by this build) shows every
        # <consonant>+्+र pair fuses into its own dedicated glyph, but the
        # *visual content* is consistently "the base consonant, plus this
        # one reusable diagonal tail" - so, exactly like ്ര, it's recorded
        # once and composed generically (see _composable_marks below) at
        # the accepted cost of not reproducing the font's exact per-pair
        # kerning (docs/ARCHITECTURE.md's "Compound vowel signs" section
        # documents this same trade-off for Malayalam). Give the recorder
        # a real reference ghost the same way.
        inputs.append(virama + "र")

    return inputs


def _consonant_matra_inputs(chars: object) -> list[str]:
    """Consonant + dependent vowel (every syllable), including rare matras.

    Also brute-forces consonant+nukta (e.g. क + ़ = क़), if the language has
    one - real per-consonant shaping, not just the generic mark recipe, is
    what actually lets Agent 2 verify whether nukta fuses into a
    consonant-specific shape (the way some Malayalam matras do) or stays a
    plain separate mark. Restricted to the main `consonants` set, not
    `rare_consonants` - nukta exists specifically for sounds Sanskrit
    doesn't have, so pairing it with Sanskrit-loanword-tier consonants has
    no real-world basis.
    """
    consonants = char_tuple(chars, "CONSONANTS")
    rare_consonants = char_tuple(chars, "RARE_CONSONANTS")
    matras = char_tuple(chars, "MATRAS")
    rare_matras = char_tuple(chars, "RARE_MATRAS")
    nukta = getattr(chars, "NUKTA", None)
    single_marks = matras + rare_matras + ((nukta,) if nukta else ())
    inputs = [c + m for c in consonants for m in single_marks]
    inputs += [c + m for c in rare_consonants for m in matras]
    return inputs


def _conjunct_inputs(chars: object) -> list[str]:
    """Conjuncts: consonant + virama + consonant.

    consonant+virama (dead-consonant forms) and conjunct+matra are NOT
    brute-forced here - that's a combinatorial explosion for little gain.
    Both compose cleanly at runtime from a base cluster + a mark's
    prefix/suffix recipe - see `_build_marks()` below and
    `js/src/index.js`'s `composeCluster()`.
    """
    virama = getattr(chars, "VIRAMA", None)
    consonants = char_tuple(chars, "CONSONANTS")
    if not virama:
        return []
    return [c1 + virama + c2 for c1 in consonants for c2 in consonants]


def _anusvara_visarga_inputs(chars: object) -> list[str]:
    """Independent vowels and consonants + anusvara / visarga."""
    bases = (
        char_tuple(chars, "INDEPENDENT_VOWELS")
        + char_tuple(chars, "RARE_VOWELS")
        + char_tuple(chars, "CONSONANTS")
    )
    marks = [m for m in (getattr(chars, "ANUSVARA", None), getattr(chars, "VISARGA", None)) if m]
    return [b + mark for b in bases for mark in marks]


def _build_input_list(lang: LanguageSpec, chars: object) -> list[str]:
    """Return all Unicode cluster strings to be shaped, deduplicated in order."""
    inputs = (
        _standalone_inputs(lang, chars)
        + _consonant_matra_inputs(chars)
        + _conjunct_inputs(chars)
        + _anusvara_visarga_inputs(chars)
    )

    seen: set[str] = set()
    unique: list[str] = []
    for item in inputs:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _shape_all(inputs: list[str], font: str) -> dict:
    """Shape every input cluster and collect results.

    Returns
    -------
    dict
        ``{"meta": {...}, "clusters": {cluster: {"glyphs": [...], "advance": N}}}``
    """
    result: dict = {"meta": None, "clusters": {}}
    ok = skipped = 0

    for inp in inputs:
        if inp in result["clusters"]:
            continue
        try:
            trace = shape_word(inp, font)
        except Exception as exc:
            print(f"  skip {inp!r}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        if result["meta"] is None:
            result["meta"] = {
                "unitsPerEm": trace["unitsPerEm"],
                "ascent": trace["ascent"],
                "descent": trace["descent"],
            }

        result["clusters"][inp] = {
            "glyphs": [{"d": g["d"], "x": g["x"], "y": g["y"]} for g in trace["glyphs"]],
            "advance": trace["totalAdvance"],
        }
        ok += 1

    print(f"  shaped {ok} clusters, skipped {skipped}", file=sys.stderr)
    return result


def _composable_marks(lang: LanguageSpec, chars: object) -> list[str]:
    """Return the marks composable onto an arbitrary base cluster at runtime.

    The generic part (virama, nukta, every matra, anusvara/visarga/
    candrabindu) applies to any script that has those categories at all.
    The subjoined-conjunct-tail
    marks (്യ/്വ/്ല/്ര) are a Malayalam-specific finding - which consonants,
    if any, form this kind of reduced tail form in a new script is exactly
    the sort of thing docs/LANGUAGE_ONBOARDING_AGENTS.md's Agent 1/2 exist
    to determine, not something to assume from Malayalam's list.
    """
    virama = getattr(chars, "VIRAMA", None)
    marks: list[str] = []
    if virama:
        marks.append(virama)
    nukta = getattr(chars, "NUKTA", None)
    if nukta:
        marks.append(nukta)
    marks += list(char_tuple(chars, "MATRAS"))
    marks += list(char_tuple(chars, "RARE_MATRAS"))
    au_length_mark = getattr(chars, "AU_LENGTH_MARK", None)
    if au_length_mark:
        marks.append(au_length_mark)

    if lang.code == "ml" and virama:
        marks += [virama + "യ", virama + "വ", virama + "ല", virama + "ര"]

    if lang.code == "hi" and virama:
        # ्र (rakaar/vattu) - see _standalone_inputs's matching block above
        # for the full derivation. Shaping "्र" alone confirms it's a real,
        # dedicated, generic tail glyph (not र's own full form reused) -
        # exactly the same shape of finding as Malayalam's ്ര.
        marks.append(virama + "र")

    anusvara = getattr(chars, "ANUSVARA", None)
    visarga = getattr(chars, "VISARGA", None)
    candrabindu = getattr(chars, "CANDRABINDU", None)
    if anusvara:
        marks.append(anusvara)
    if visarga:
        marks.append(visarga)
    if candrabindu:
        marks.append(candrabindu)
    return marks


def _build_marks(composable_marks: list[str], font: str) -> dict:
    """Shape each composable mark alone and split it into prefix/suffix parts.

    HarfBuzz auto-inserts a dotted-circle placeholder glyph when a combining
    mark has no preceding base - its position tells us exactly how the mark
    attaches to *any* base: glyphs before the placeholder print as a prefix;
    glyphs after it print as a suffix. See `docs/ARCHITECTURE.md`'s
    "Composition" section for the full derivation and the real bugs found
    building this for Malayalam.

    Returns
    -------
    dict
        ``{mark: {"shift": N, "prefix": [...], "suffix": [...], "trailingWidth": N}}``
    """
    marks: dict = {}
    for m in composable_marks:
        trace = shape_word(m, font)
        glyphs = trace["glyphs"]
        circle_idx = next(i for i, g in enumerate(glyphs) if g["glyphName"] == "uni25CC")
        shift = glyphs[circle_idx]["x"]
        prefix = [{"d": g["d"], "x": g["x"], "y": g["y"]} for g in glyphs[:circle_idx]]
        suffix_glyphs = glyphs[circle_idx + 1 :]
        anchor = suffix_glyphs[0]["x"] if suffix_glyphs else shift
        suffix = [{"d": g["d"], "x": g["x"] - anchor, "y": g["y"]} for g in suffix_glyphs]
        trailing_width = (trace["totalAdvance"] - anchor) if suffix_glyphs else 0.0
        marks[m] = {
            "shift": shift,
            "prefix": prefix,
            "suffix": suffix,
            "trailingWidth": trailing_width,
        }
    return marks


#: Devanagari's reph-triggering consonant - see _build_contextual_forms().
#: Hardcoded here rather than sourced from _chars_hi.py, matching this
#: file's existing precedent for rakaar (the literal "र" already appears
#: directly in _standalone_inputs's and _composable_marks's hi-gated
#: blocks above) - Hindi's own onboarding data already lives inline in
#: this tool's gated sections, not exclusively in the chars module.
_HI_REPH_CONSONANT = "र"

#: Pairs excluded from the generic half-form derivation below - verified
#: (docs/languages/hi/composition-primitives-report.md §1) to fuse into a
#: genuine ya-phala-style ligature instead of using the base consonant's
#: ordinary half-form shape. Structurally the same category as any true
#: akhand ligature - recorded/composed directly, not via contextualForms.
#:
#: Written via chr() for the two nukta consonants, not literal characters -
#: same silent-NFD-round-trip trap _chars_hi.py's NUKTA_CONSONANTS docstring
#: warns about (confirmed here too: a literal "ड़"/"ढ़" typed directly into
#: this file previously got silently decomposed on save, so this set's keys
#: never matched `consonants`' precomposed codepoints and the exclusion was
#: a silent no-op - harmless only by coincidence, since "क" already
#: satisfies the "one representative partner" loop below for both
#: consonants before "य" is ever reached).
_HI_HALFFORM_EXCLUDED_PAIRS = {(chr(0x95C), "य"), (chr(0x95D), "य")}


def _extract_ghost(own_glyph: dict, other_glyph: dict) -> dict:
    """Build a standalone-ghost-shaped entry for one glyph pulled out of an
    already-shaped 2-glyph cluster entry.

    Re-anchors ``own_glyph`` to x=0, matching the convention every other
    standalone atom's ghost already follows (see `_shape_all` - a
    freshly-shaped standalone cluster's first glyph starts at or near 0).
    ``advance`` is approximated as the horizontal gap to `other_glyph` in
    the source pair - this ghost is never itself rendered as a real
    standalone cluster (see `_build_contextual_forms`'s docstring for why),
    so its exact advance is only ever used for the recorder's own display
    layout, not for real composition math.
    """
    anchor = own_glyph["x"]
    return {
        "glyphs": [{"d": own_glyph["d"], "x": 0.0, "y": own_glyph["y"]}],
        "advance": abs(other_glyph["x"] - anchor),
    }


def _build_contextual_forms(lang: LanguageSpec, chars: object, shaped_clusters: dict) -> dict:
    """Derive Devanagari's half-form/reph substitute atoms (hi-gated).

    `docs/languages/hi/labeling-worklist.md`'s "headline finding": a
    virama between two consonants almost never produces its own glyph, so
    neither existing composition mechanism (mark recipes, per-character
    fallback) fits half-forms (the *base* consonant substitutes a
    different shape) or reph (the mark detaches from its own typed
    position entirely). `docs/languages/hi/composition-primitives-report.md`
    verifies the fix: each consonant's half-form, and the reph hook, really
    is one single reusable glyph shape - but that shape must be pulled out
    of an already-shaped `<consonant><virama><consonant>` cluster entry
    (from `_conjunct_inputs()`'s brute-force sweep, already in
    `shaped_clusters`), never obtained by shaping the 2-character trigger
    standalone: that instead produces the *linguistically different*
    word-final "explicit halant" glyph (confirmed empirically, not
    assumed - see that report's §3), which is also the glyph real running
    text ending in that trigger correctly needs, via virama's own
    pre-existing `marks` entry.

    That's exactly why this returns a *separate* `contextualForms` table
    rather than adding `<consonant><virama>` entries to `clusters` (what
    every other atom in this file does): a `clusters["<C1><virama>"]`
    entry would make `resolveSegments`'s direct-match tier pick up real
    word-final `<C1><virama>` text and render it as the mid-conjunct
    half-form - silently wrong. Keeping the ghost data out of `clusters`
    entirely, reachable only via `contextualForms[trigger]["ghost"]`,
    means only the recorder (for tracing) and the new
    `tryComposeContextualForm`/`compose_contextual_form` composition
    functions (via `STROKE_LIBRARY[trigger]` once traced - a namespace
    `resolveSegments` never consults) ever see it; real text segmentation
    is completely unaffected and untouched.

    Returns
    -------
    dict
        ``{"<C1><virama>": {"role": "halfForm" | "reph", "ghost": {...}}}``,
        empty for every language but Hindi.
    """
    if lang.code != "hi":
        return {}
    virama = getattr(chars, "VIRAMA", None)
    consonants = char_tuple(chars, "CONSONANTS")
    if not virama:
        return {}

    forms: dict = {}

    for c1 in consonants:
        if c1 == _HI_REPH_CONSONANT:
            continue
        for c2 in consonants:
            if (c1, c2) in _HI_HALFFORM_EXCLUDED_PAIRS:
                continue
            entry = shaped_clusters.get(c1 + virama + c2)
            if not entry or len(entry["glyphs"]) != 2:
                continue
            g0, g1 = entry["glyphs"]
            forms[c1 + virama] = {"role": "halfForm", "ghost": _extract_ghost(g0, g1)}
            break  # one representative partner suffices - identity verified per-consonant

    for c2 in consonants:
        entry = shaped_clusters.get(_HI_REPH_CONSONANT + virama + c2)
        if not entry or len(entry["glyphs"]) != 2:
            continue
        g0, g1 = entry["glyphs"]
        forms[_HI_REPH_CONSONANT + virama] = {"role": "reph", "ghost": _extract_ghost(g1, g0)}
        break  # reph hook shape verified identical across all 40 partners

    return forms


def _runtime_quirks(lang: LanguageSpec, chars: object, shaped_clusters: dict) -> dict:
    """Return the language-specific lookup tables js/src/index.js needs at runtime.

    Written into glyph-data.json as top-level ``legacyEncodings``/
    ``splitVowelParts``/``contextualForms`` keys, present only for a
    language that actually has them - a language with none of these
    (everything but Malayalam and Hindi, today) gets no extra keys at all,
    so index.js never has anything script-specific to load, hold in
    memory, or iterate for that language's session. See
    `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s "Don't generalize from Malayalam"
    - a future language's own runtime quirks, if it has any, are a finding
    from *its* onboarding, added here the same gated way, not inherited.

    Returns
    -------
    dict
        Zero or more of ``{"legacyEncodings": {...}, "splitVowelParts": {...},
        "contextualForms": {...}}``.
    """
    quirks: dict = {}
    if lang.code == "ml":
        quirks["legacyEncodings"] = _ML_LEGACY_CHILLU
        quirks["splitVowelParts"] = _ML_SPLIT_VOWEL_PARTS
    if lang.code == "hi":
        quirks["legacyEncodings"] = _HI_NUKTA_CONSONANTS
        contextual_forms = _build_contextual_forms(lang, chars, shaped_clusters)
        if contextual_forms:
            quirks["contextualForms"] = contextual_forms
    return quirks


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "font",
        nargs="?",
        default=None,
        help="Path to a .ttf/.otf font file. Defaults to the language's bundled "
        "fixture font, if it has one (Malayalam only, today).",
    )
    parser.add_argument(
        "--lang",
        default="malayalam",
        help="Registry key from jayasree.languages.LANGUAGES (default: malayalam).",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: shape all clusters for --lang and write its glyph-data.json."""
    args = _parse_args()
    lang = get_language(args.lang)

    font_path = args.font or lang.resolved_default_font()
    if font_path is None:
        raise SystemExit(
            f"No bundled default font for {lang.name!r} - pass a font path explicitly, "
            f"e.g. python tools/build_glyph_data.py /path/to/Font.ttf --lang {args.lang}"
        )

    chars = lang.chars()
    inputs = _build_input_list(lang, chars)
    result = _shape_all(inputs, str(font_path))
    result["marks"] = _build_marks(_composable_marks(lang, chars), str(font_path))
    result.update(_runtime_quirks(lang, chars, result["clusters"]))

    out_path = data_paths(lang).glyph_data
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

    size_kb = out_path.stat().st_size // 1024
    print(
        f"Written {out_path.relative_to(ROOT)}  ({size_kb} KB, {len(result['clusters'])} clusters)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
