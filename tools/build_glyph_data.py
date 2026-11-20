#!/usr/bin/env python3
"""Pre-compute SVG glyph paths for a language's cluster inventory and write glyph-data.json.

Language-parametrized (Phase 0 of docs/LANGUAGE_ONBOARDING_AGENTS.md) via
`--lang`, defaulting to Malayalam (Hindi is onboarded too).
Every language's own quirks (Malayalam's subjoined-conjunct marks and split
compound vowels; Hindi's rakaar/vattu composition, nukta encoding duality,
and half-form/reph derivation via `contextualForms`) are gated behind
`lang.code == "<code>"` rather than assumed for every script - a new
language's equivalent quirks get discovered by that pipeline's Agent 1/2 and
added as their own gated block, not inherited from an existing language's.

This project does not keep any language's real research out of this public
file - every onboarded language's quirks live inline here, openly, same as
Malayalam's. (An earlier revision of this file routed Hindi's quirks through
a private, env-var-selected extension module; that mechanism has been
removed - see git history around `data(hi): inline Hindi's build extension`
if you need the old shape for reference.)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import svgpathtools

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

#: Devanagari's reph-triggering consonant.
_HI_REPH_CONSONANT = "र"

#: Pairs excluded from the generic half-form derivation in
#: `_hi_extract_contextual_forms()` below - a consonant whose *ordinary*
#: half-form shape (used before most following consonants) is verified
#: identical across nearly every partner, but which shapes as a distinctly
#: *different* 2-glyph pair (same glyph count, different glyph[0] path) for
#: one or two specific partners - docs/languages/hi/README.md ("The headline
#: finding") verifies this per font. Derived for Noto Sans Devanagari
#: (2026-09-06 font re-evaluation, see font-report.md's "Re-evaluation"
#: section) - **not the same pairs Annapurna SIL needed**: Annapurna's
#: exceptions were ड़/ढ़ before य (a ya-phala-style fusion); under Noto,
#: ड़्य/ढ़्य are instead plain 3-glyph explicit-halant fallthroughs
#: (chars == glyphs, already generically composable, no exclusion needed
#: at all), while Noto's own real exceptions are six different pairs found
#: by an exhaustive glyph-identity sweep across all 39 non-र consonants'
#: partners: छर (छ's ordinary half-form differs before र), जज (ज before ज
#: itself), नथ/नध (न before थ/ध), मभ (म before भ), and ज़ज (ज़ before ज) -
#: confirmed structurally, not guessed: every one of these six is still a
#: genuine 2-glyph pair (not a single-glyph akhand fusion), just with a
#: glyph[0] path that doesn't match that consonant's own majority shape
#: found across its other 36-38 partners. Recorded/composed directly (own
#: `clusters` entry takes priority over `tryComposeContextualForm` at
#: runtime - see js/src/index.js's STROKE_LIBRARY-first lookup order), same
#: as any true akhand ligature.
#:
#: This is font-specific data, not a general Devanagari fact - re-run the
#: identity sweep (group each consonant's 2-glyph partners by
#: `glyphs[0]["d"]`, flag any consonant with >1 distinct group) whenever
#: Hindi's ghost font changes again, rather than assuming these six
#: transfer. ज़/ड़ etc. written via chr() for the nukta codepoint (ज़), not
#: a literal character - see _chars_hi.py's NUKTA_CONSONANTS docstring for
#: the silent-NFD-round-trip trap this avoids.
_HI_HALFFORM_EXCLUDED_PAIRS = {
    ("छ", "र"),
    ("ज", "ज"),
    ("न", "थ"),
    ("न", "ध"),
    ("म", "भ"),
    (chr(0x95B), "ज"),
}

#: Hindi's encoding-duality case, direct parallel to Malayalam's chillu
#: legacy spellings: every one of these 7 nukta consonants has a real
#: Unicode *canonical* NFD decomposition into base-consonant + U+093C
#: (verified directly via `unicodedata.decomposition()` while building this
#: table). Real text mixes both spellings unpredictably, and this font
#: shapes both to the exact same single fused glyph (verified via
#: HarfBuzz), so - same as chillu - one recorded atom (the precomposed
#: codepoint, kept in the standard CONSONANTS set) covers both spellings
#: once the decomposed one normalizes to it here.
# Precomposed codepoints written as chr(0x...) rather than literal
# characters - a literal precomposed nukta letter in source text is
# visually indistinguishable from (and too easy for an editor/tool to
# silently NFC/NFD-normalize into) its own decomposed form, which would
# make the *values* below equal to the *keys*, silently turning this table
# into a no-op. chr() sidesteps that entirely.
_HI_NUKTA_BASE = "कखगजडढफ"  # क ख ग ज ड ढ फ
#: Precomposed codepoints written via chr() rather than literal characters -
#: a literal precomposed nukta letter in source text is visually
#: indistinguishable from (and too easy for an editor/tool to silently
#: NFC/NFD-normalize into) its own decomposed form, which would make this
#: tuple's entries equal to `_HI_NUKTA_BASE + _HI_NUKTA_MARK` and silently
#: turn `_HI_NUKTA_CONSONANTS` below into a no-op. chr() sidesteps that
#: entirely - see _chars_hi.py's NUKTA_CONSONANTS docstring for the same
#: trap.
_HI_NUKTA_PRECOMPOSED = tuple(chr(cp) for cp in (0x958, 0x959, 0x95A, 0x95B, 0x95C, 0x95D, 0x95E))
_HI_NUKTA_MARK = "़"  # ़
_HI_NUKTA_CONSONANTS: dict[str, str] = {
    base + _HI_NUKTA_MARK: precomposed
    for base, precomposed in zip(_HI_NUKTA_BASE, _HI_NUKTA_PRECOMPOSED, strict=True)
}

#: Of the 7 nukta consonants, these 5 are verified (byte-identical first
#: SVG subpath, checked directly against this build's own shaped
#: `clusters` while deriving this table) to be *exactly* their plain base
#: consonant's own outline plus one small additional dot contour at a
#: font-given position - genuinely decomposable, unlike ख़/फ़ below.
#: Keyed by the nukta consonant (chr() - see this file's NFD-round-trip
#: warning above), value is its plain base consonant. Used by
#: `tools/process_strokes.py`'s own `_hi_derive_strokes()` to synthesize
#: these 5 consonants' strokes from already-recorded parts - see that
#: function's docstring, not this file (this table is shared between the
#: two tools, duplicated rather than imported across them since
#: `validate_data.py`-style scripts in this project stay dependency-light
#: by convention).
#:
#: ख़ (chr(0x959)) and फ़ (chr(0x95E)) are deliberately excluded: the same
#: check shows their first subpath does *not* match the plain ख/फ outline
#: - Noto draws a genuinely different base shape for them, same category
#: as a true akhand ligature - real atoms, not derivable, however tempting
#: the "consonant + dot" pattern looks for the other five.
#:
#: Font-specific data, not a Devanagari-wide fact - re-run the subpath
#: check (`shaped_clusters[nukta][...]["glyphs"][0]["d"]`'s first `M...`
#: segment vs. the plain base's own) whenever Hindi's ghost font changes.
_HI_DECOMPOSABLE_NUKTA_BASE: dict[str, str] = {
    chr(0x958): "क",
    chr(0x95A): "ग",
    chr(0x95B): "ज",
    chr(0x95C): "ड",
    chr(0x95D): "ढ",
}

#: Shown by tools/stroke-recorder.js as a persistent banner while Hindi's
#: data is loaded - the shirorekha (headline) is a *synthetic, word-level*
#: stroke by design (docs/languages/hi/README.md), never a
#: per-character traced one. Every ghost outline still shows it (it's part
#: of the font's own glyph outline), so without an explicit notice a tracer
#: has no way to know to skip it.
_HI_RECORDER_NOTE = (
    "Devanagari's shirorekha (the horizontal line along the top of each "
    "letter) is generated automatically when words are composed - do not "
    "trace it. Skip the top line entirely for every character; only draw "
    "the strokes below it."
)

#: The shirorekha (headline) band's y-range, in this build's own SVG-space
#: font units (unitsPerEm = 1000 for Noto Sans Devanagari) - verified
#: directly against real rasterized outlines, not estimated. See
#: docs/languages/hi/README.md's "A real structural difference
#: from Annapurna, found immediately" and "Headline gaps in rounded-loop
#: letters" sections. Consumed generically by js/src/index.js's synthetic
#: word-level shirorekha-stroke logic via `glyphData.shirorekha.y0`/`.y1` -
#: index.js has no Hindi-specific knowledge of this value, same as every
#: other per-language quirk in this file.
#:
#: Font-specific data, not a Devanagari-wide fact - re-measure (rasterize
#: real outlines at the headline's approximate y, per that report's
#: "Method" section) whenever Hindi's ghost font changes again.
_HI_SHIROREKHA_Y0 = -622.0
_HI_SHIROREKHA_Y1 = -551.0


def _hi_headline_bar_edges(d: str, y0: float, y1: float, tol: float = 1.0) -> list[float]:
    """Return x-positions of this glyph's genuine headline-bar edges.

    Mechanical replacement for a hand-measured per-letter gap table - but
    specifically for the font's *flat rectangular bar* feature, not "any
    ink present at headline height." An earlier version of this function
    swept a single horizontal line through the glyph and reported every
    ink crossing there; that over-detects, because a rounded loop/knot
    (e.g. भ/अ/आ's own top curve - see docs/languages/hi/
    README.md's "Shirorekha" section) often
    also happens to cross the same height without being the headline bar
    at all - confirmed directly: भ's loop ink at headline-mid-height
    shifts continuously from [117,244] at the band's top to split into two
    pieces by the band's bottom, while the genuine bar [402,717] stays
    bit-for-bit constant across the whole band, because it's drawn as an
    actual rectangle in the font (an explicit vertical edge at each end,
    each spanning the *entire* band height).

    Method: this font draws its headline bar as a literal rectangle - a
    straight vertical line segment at each edge, each one running the full
    [y0, y1] band height (confirmed against the raw path commands - e.g.
    "...H402V-622H717V-551...": a vertical line from (402, -551) to
    (402, -622), exactly the band's own height). This walks every `Line`
    segment in the path and keeps only ones that are vertical (constant x)
    and whose y-span covers the *entire* band - a loop/knot's own curve
    never produces such a segment, since nothing about its shape is a
    flat-sided rectangle spanning the full band height.

    Parameters
    ----------
    d : str
        A single glyph's own SVG path (``glyphs[i]["d"]``), in that glyph's
        own local coordinate frame (caller offsets the result, not this
        function - see `_hi_cluster_ink_ranges`).
    y0, y1 : float
        The headline band's own y-range (`_HI_SHIROREKHA_Y0`/`_Y1`).
    tol : float
        Slack (font units) for "spans the full band" and "is vertical,"
        to absorb float rounding in the font's own coordinates.

    Returns
    -------
    list[tuple[float, float]]
        Sorted, merged ``(start, end)`` ink spans, already unioned across
        every subpath in the glyph - a glyph can have more than one
        rectangular bar contour (e.g. ऊ's single glyph bakes in both उ's
        own base-shape bar *and* its own length-extension's bar, each a
        separate, overlapping rectangle: [0,563] and [300,800]). Edges are
        paired up *within* each subpath first (even/odd by the standard
        even-odd fill rule, which holds for one simple closed contour),
        not globally across the whole glyph - sorting and pairing every
        subpath's edges together as one flat list is wrong whenever two
        such rectangles overlap, since it reads the union as two separate
        pieces with a bogus gap in the middle instead of one continuous
        span (confirmed directly against ऊ, which otherwise produced a
        spurious hole exactly where the two rectangles overlap). Empty if
        the glyph has no genuine headline bar at all.
    """
    try:
        path = svgpathtools.parse_path(d)
    except Exception:
        return []

    band_lo, band_hi = min(y0, y1), max(y0, y1)
    spans: list[tuple[float, float]] = []
    for sub in path.continuous_subpaths():
        xs: list[float] = []
        for seg in sub:
            if not isinstance(seg, svgpathtools.Line):
                continue
            x_start, y_start = seg.start.real, seg.start.imag
            x_end, y_end = seg.end.real, seg.end.imag
            if abs(x_start - x_end) > tol:
                continue  # not vertical
            seg_lo, seg_hi = min(y_start, y_end), max(y_start, y_end)
            if seg_lo <= band_lo + tol and seg_hi >= band_hi - tol:
                xs.append((x_start + x_end) / 2)
        xs.sort()
        if len(xs) % 2:
            xs = xs[:-1]  # an unpaired edge can't form a span - drop it
        spans.extend((xs[i], xs[i + 1]) for i in range(0, len(xs), 2))

    spans.sort()
    merged: list[tuple[float, float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1] + tol:
            merged[-1] = (merged[-1][0], max(merged[-1][1], x1))
        else:
            merged.append((x0, x1))
    return merged


def _hi_cluster_ink_ranges(
    glyphs: list[dict], y0: float, y1: float, cache: dict[str, list[tuple[float, float]]]
) -> list[list[float]]:
    """Union every glyph's own (offset) headline-bar ranges for one cluster.

    `cache` memoizes `_hi_headline_bar_edges` by each glyph's own `d`
    string - across ~2400 clusters the same handful of glyph shapes (a
    base consonant, a matra, a virama) repeat constantly, so this turns a
    build-time cost that would otherwise be "rasterize once per cluster"
    into "rasterize once per distinct glyph outline," which is what makes
    computing this per *exact cluster* (not just per standalone base
    character) cheap enough to do for every cluster unconditionally.

    Ranges are returned already offset into the cluster's own absolute
    coordinate frame (each glyph's `x`/`y` added in) - js/src/index.js can
    position them directly against a group's `groupX`, no base-character
    lookup or advance-scaling needed.
    """
    ranges: list[list[float]] = []
    for g in glyphs:
        d = g["d"]
        if d not in cache:
            cache[d] = _hi_headline_bar_edges(d, y0 - g["y"], y1 - g["y"])
        for x0, x1 in cache[d]:
            ranges.append([x0 + g["x"], x1 + g["x"]])
    ranges.sort(key=lambda r: r[0])
    return ranges


def _hi_extract_contextual_forms(
    chars: object, shaped_clusters: dict, extract_ghost: Callable[[dict, dict], dict]
) -> dict:
    """Derive Devanagari's half-form/reph substitute atoms.

    docs/languages/hi/README.md's "headline finding": a virama
    between two consonants almost never produces its own glyph, so neither
    existing composition mechanism (mark recipes, per-character fallback)
    fits half-forms (the *base* consonant substitutes a different shape) or
    reph (the mark detaches from its own typed position entirely).
    composition-primitives-report.md verifies the fix: each consonant's
    half-form, and the reph hook, really is one single reusable glyph
    shape - but that shape must be pulled out of an already-shaped
    `<consonant><virama><consonant>` cluster entry (already in
    `shaped_clusters`), never obtained by shaping the 2-character trigger
    standalone: that instead produces the *linguistically different*
    word-final "explicit halant" glyph (confirmed empirically, not assumed
    - see that report's §3), which is also the glyph real running text
    ending in that trigger correctly needs, via virama's own pre-existing
    `marks` entry.

    That's exactly why this returns a *separate* `contextualForms` table
    rather than adding `<consonant><virama>` entries to `clusters`: a
    `clusters["<C1><virama>"]` entry would make `resolveSegments`'s
    direct-match tier pick up real word-final `<C1><virama>` text and
    render it as the mid-conjunct half-form - silently wrong. Keeping the
    ghost data out of `clusters` entirely, reachable only via
    `contextualForms[trigger]["ghost"]`, means only the recorder (for
    tracing) and `tryComposeContextualForm`/`compose_contextual_form` (via
    `STROKE_LIBRARY[trigger]` once traced - a namespace `resolveSegments`
    never consults) ever see it; real text segmentation is completely
    unaffected and untouched.

    Returns
    -------
    dict
        ``{"<C1><virama>": {"role": "halfForm" | "reph", "ghost": {...}}}``.
    """
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
            forms[c1 + virama] = {"role": "halfForm", "ghost": extract_ghost(g0, g1)}
            break  # one representative partner suffices - identity verified per-consonant

    for c2 in consonants:
        entry = shaped_clusters.get(_HI_REPH_CONSONANT + virama + c2)
        if not entry or len(entry["glyphs"]) != 2:
            continue
        g0, g1 = entry["glyphs"]
        forms[_HI_REPH_CONSONANT + virama] = {"role": "reph", "ghost": extract_ghost(g1, g0)}
        break  # reph hook shape verified identical across all 40 partners

    return forms


def _hi_extract_true_ligatures(chars: object, shaped_clusters: dict) -> list[str]:
    """Return every `<C1><virama><C2>` cluster that needs its own direct trace.

    This is the other half of docs/languages/hi/README.md's
    Group D (47 true akhand ligatures + 6 half-form exceptions, 53 total) -
    computed mechanically here, reusing `shaped_clusters` (this build's own
    HarfBuzz output) rather than hand-copying the doc's prose list, so it
    never drifts from what the current font actually shapes. Written into
    glyph-data.hi.json as `knownAtoms` so tools/stroke-recorder.js's generic
    `isAtom()` shows these by default instead of requiring each one typed
    into "+ Add custom cluster" from memory.

    Two categories, both genuinely unrecoverable from any other recorded
    atom (same reasoning as any true ligature - see
    composition-primitives-report.md):

    - **True single-glyph fusions**: `len(glyphs) == 1`, excluding reph
      (`c1 == _HI_REPH_CONSONANT`, glyph-reordering, not a fusion) and
      rakaar (`c2 == _HI_REPH_CONSONANT`, already generic via the `्र` mark
      from the `lang.code == "hi"` block in `_composable_marks()` below) -
      those two *also* produce one or two glyphs but already compose
      without a direct trace.
    - **Half-form exceptions**: `_HI_HALFFORM_EXCLUDED_PAIRS` - a genuine
      2-glyph pair, excluded from `_hi_extract_contextual_forms()`'s
      generic half-form derivation specifically because this pair's shape
      isn't the consonant's majority half-form.
    """
    virama = getattr(chars, "VIRAMA", None)
    consonants = char_tuple(chars, "CONSONANTS")
    if not virama:
        return []

    ligatures: list[str] = []
    for c1 in consonants:
        for c2 in consonants:
            key = c1 + virama + c2
            entry = shaped_clusters.get(key)
            if not entry:
                continue
            n_glyphs = len(entry["glyphs"])
            is_true_fusion = n_glyphs == 1 and c1 != _HI_REPH_CONSONANT and c2 != _HI_REPH_CONSONANT
            is_halfform_exception = n_glyphs == 2 and (c1, c2) in _HI_HALFFORM_EXCLUDED_PAIRS
            if is_true_fusion or is_halfform_exception:
                ligatures.append(key)
    return ligatures


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
        # (docs/languages/hi/README.md's "Native punctuation" section).
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
    # distinct from anusvara - see docs/languages/hi/README.md) is the
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
        # Devanagari analogue of Malayalam's ്ര above: an exhaustive 33x33
        # sweep (docs/languages/hi/README.md) shows every
        # <consonant>+्+र pair fuses into its own dedicated glyph, but the
        # *visual content* is consistently "the base consonant, plus this
        # one reusable diagonal tail" - so, exactly like ്ര, it's recorded
        # once and composed generically (see the `lang.code == "hi"` block
        # in `_composable_marks()` below) at the accepted cost of not
        # reproducing the font's exact per-pair kerning.
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
        # ्र as a composable mark - see the `lang.code == "hi"` block in
        # `_standalone_inputs()` above. Shaping "्र" alone confirms it's a
        # real, dedicated, generic tail glyph (not र's own full form
        # reused) - exactly the same shape of finding as Malayalam's ്ര.
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


def _extract_ghost(own_glyph: dict, other_glyph: dict) -> dict:
    """Build a standalone-ghost-shaped entry for one glyph pulled out of an
    already-shaped 2-glyph cluster entry.

    Re-anchors ``own_glyph`` to x=0, matching the convention every other
    standalone atom's ghost already follows (see `_shape_all` - a
    freshly-shaped standalone cluster's first glyph starts at or near 0).
    ``advance`` is approximated as the horizontal gap to `other_glyph` in
    the source pair - exposed for a build extension's own contextual-form
    derivation to reuse (e.g. Devanagari half-form/reph ghosts), so each
    language doesn't need to reimplement this geometry. Never itself
    rendered as a real standalone cluster, so its exact advance is only
    ever used for the recorder's own display layout, not for real
    composition math.
    """
    anchor = own_glyph["x"]
    return {
        "glyphs": [{"d": own_glyph["d"], "x": 0.0, "y": own_glyph["y"]}],
        "advance": abs(other_glyph["x"] - anchor),
    }


def _runtime_quirks(lang: LanguageSpec, chars: object, shaped_clusters: dict) -> dict:
    """Return the language-specific lookup tables js/src/index.js needs at runtime.

    Written into glyph-data.json as top-level ``legacyEncodings``/
    ``splitVowelParts``/``contextualForms``/``knownAtoms`` keys, present
    only for a language that actually has them - a language with none of
    these gets no extra keys at all, so index.js never has anything
    script-specific to load, hold in memory, or iterate for that
    language's session. See `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s "Don't
    generalize from Malayalam" - a future language's own runtime quirks,
    if it has any, are a finding from *its* onboarding, added here the
    same gated way, not inherited.

    Returns
    -------
    dict
        Zero or more of ``{"legacyEncodings": {...}, "splitVowelParts": {...},
        "contextualForms": {...}, "knownAtoms": [...], "shirorekha": {...}}``.
    """
    quirks: dict = {}
    if lang.code == "ml":
        quirks["legacyEncodings"] = _ML_LEGACY_CHILLU
        quirks["splitVowelParts"] = _ML_SPLIT_VOWEL_PARTS
    if lang.code == "hi":
        quirks["legacyEncodings"] = _HI_NUKTA_CONSONANTS
        contextual_forms = _hi_extract_contextual_forms(chars, shaped_clusters, _extract_ghost)
        if contextual_forms:
            quirks["contextualForms"] = contextual_forms
        known_atoms = _hi_extract_true_ligatures(chars, shaped_clusters)
        if known_atoms:
            quirks["knownAtoms"] = known_atoms
        # Ink ranges are computed per *exact composed cluster* (not per
        # standalone base character) - a key difference from an earlier
        # version of this table, which only covered standalone base
        # letters and left a matra-shaped gap for any composed cluster
        # (e.g. भा left ा's own contribution uncovered). Computing it per
        # cluster instead means every cluster - plain letters, matra
        # attachments, conjuncts - is correct automatically, with no
        # base-character lookup/startsWith matching needed in
        # js/src/index.js at all (see `_hi_cluster_ink_ranges`'s docstring
        # for why this is still cheap: memoized by each glyph's own `d`
        # string, not recomputed per cluster).
        ink_cache: dict[str, list[tuple[float, float]]] = {}
        ink_ranges = {}
        for cluster, entry in shaped_clusters.items():
            ranges = _hi_cluster_ink_ranges(
                entry["glyphs"], _HI_SHIROREKHA_Y0, _HI_SHIROREKHA_Y1, ink_cache
            )
            if ranges:
                ink_ranges[cluster] = ranges
        quirks["shirorekha"] = {
            "y0": _HI_SHIROREKHA_Y0,
            "y1": _HI_SHIROREKHA_Y1,
            "inkRanges": ink_ranges,
        }
    return quirks


def _recorder_note(lang: LanguageSpec) -> str | None:
    """Return the recorder-banner text for `lang`, or None if it needs none.

    Separate from `_runtime_quirks()` on purpose - that function's output
    feeds js/src/index.js's runtime composer; this one is read only by
    tools/stroke-recorder.js and has no effect on composition.
    """
    if lang.code == "hi":
        return _HI_RECORDER_NOTE
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "font",
        nargs="?",
        default=None,
        help="Path to a .ttf/.otf font file. Defaults to the language's bundled "
        "fixture font, if it has one (Malayalam has one; Hindi does not).",
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
    if lang.code == "hi":
        # Devanagari pedagogical convention: every matra is *written* after
        # its base consonant, even a visually-prefix one like ि (which
        # attaches to the base's left but is still the second stroke drawn,
        # not the first) - unlike Malayalam's cursive െ/േ/ൈ, which genuinely
        # are drawn before their base (a real, long-standing design choice -
        # see js/src/index.js's applyMarkStroke). This only adds a field to
        # Hindi's own marks table; Malayalam's marks table never gets it, so
        # applyMarkStroke's existing mark-first order is unchanged there.
        for mark in result["marks"].values():
            if mark["prefix"]:
                mark["writeAfterBase"] = True
    result.update(_runtime_quirks(lang, chars, result["clusters"]))

    # Read by tools/stroke-recorder.js for the page title/heading and the
    # "Add custom cluster" placeholder - present for every language (not
    # gated), so the recorder never falls back to a different script's text.
    if lang.native_name:
        result["meta"]["projectNameNative"] = lang.native_name
    if lang.example_custom_cluster:
        result["meta"]["exampleCustomCluster"] = lang.example_custom_cluster

    note = _recorder_note(lang)
    if note:
        result["meta"]["recorderNote"] = note

    out_path = data_paths(lang).glyph_data
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

    # out_path is relative to ROOT in the common case, but fall back to the
    # absolute path rather than assuming it always is.
    try:
        shown_path = out_path.relative_to(ROOT)
    except ValueError:
        shown_path = out_path
    size_kb = out_path.stat().st_size // 1024
    print(
        f"Written {shown_path}  ({size_kb} KB, {len(result['clusters'])} clusters)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
