"""Complete Unicode character inventory for Hindi (Devanagari script).

Promoted from `docs/languages/hi/chars.json` (Agent 1's structured
inventory, agent-reviewed and project-owner-approved - see
`docs/languages/hi/profile.md`'s "Resolved" section), per
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 3 step 1. Mirrors `_chars.py`'s
shape (tuple constants, fine-grained + combined tuples) but is not a copy
of its category set - Devanagari's actual structure needed three category
names Malayalam never had (`CANDRABINDU`, `NUKTA`, `NATIVE_PUNCTUATION`,
already generically supported by `languages.py`/`build_glyph_data.py`) plus
one more found here (`RARE_MARKS`, for avagraha/Om - see that module's
docstring for the same "optional, additive, gated" pattern). See
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s "Don't generalize from Malayalam" -
Devanagari has no chillu-equivalent bare-consonant form, so `CHILLU` is
simply omitted here (falls back to `()` via `char_tuple`).
"""

from __future__ import annotations

__all__ = [
    "ANUSVARA",
    "CANDRABINDU",
    "CONSONANTS",
    "CORE_INDEPENDENT_VOWELS",
    "CORE_MATRAS",
    "INDEPENDENT_VOWELS",
    "LOAN_MATRAS",
    "LOAN_VOWELS",
    "MATRAS",
    "NATIVE_PUNCTUATION",
    "NUKTA",
    "NUKTA_CONSONANTS",
    "NUMERALS",
    "RARE_MARKS",
    "RARE_MATRAS",
    "RARE_VOWELS",
    "STANDARD_CONSONANTS",
    "VIRAMA",
    "VISARGA",
]

#: 11 standard independent vowels, taught in every school varnamala.
CORE_INDEPENDENT_VOWELS: tuple[str, ...] = tuple("अआइईउऊऋएऐओऔ")

#: 2 modern loan-vowel letters (candra e/o, for English/other loanword
#: sounds not native to Hindi - बैंक, कॉलेज). Distinct codepoints from their
#: matra forms (LOAN_MATRAS below) - see docs/languages/hi/profile.md's
#: "Independent vowels" section for why the two must never be conflated.
LOAN_VOWELS: tuple[str, ...] = ("ऍ", "ऑ")

#: All in-scope independent vowels (RESOLVED, profile.md #5: loan vowels
#: are in scope, full generic treatment - no differentiated handling from
#: the core 11 the way RARE_VOWELS below gets).
INDEPENDENT_VOWELS: tuple[str, ...] = CORE_INDEPENDENT_VOWELS + LOAN_VOWELS

#: 3 rare, Sanskrit-loanword-only independent vowels (vocalic L/RR/LL) -
#: essentially never appear in native Hindi vocabulary.
RARE_VOWELS: tuple[str, ...] = ("ऌ", "ॠ", "ॡ")

#: 33 standard consonants (velar -> palatal -> retroflex -> dental ->
#: labial, then nasals/approximants/sibilants), contiguous U+0915-U+0939
#: minus the Marathi/Dravidian-transliteration letters that sit in the same
#: range but aren't Hindi's (ऩ, ऱ, ळ, ऴ - see profile.md).
STANDARD_CONSONANTS: tuple[str, ...] = tuple("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")

#: 7 nukta-modified consonants (precomposed codepoints, U+0958-095E) for
#: Perso-Arabic/English loan sounds - font-gated scope (RESOLVED,
#: profile.md #1): all 7 are in scope since the chosen font (Annapurna SIL)
#: renders all of them (docs/languages/hi/font-report.md). Also exist as
#: decomposed `consonant + ़ (NUKTA)` sequences in real text - see NUKTA
#: below and profile.md's encoding-duality note; both spellings need to
#: resolve to the same rendering (see build_glyph_data.py's
#: `_HI_NUKTA_CONSONANTS`/`legacyEncodings`).
#:
#: Written via `chr()` rather than literal characters on purpose: each of
#: these 7 codepoints has a real Unicode *canonical* NFD decomposition
#: into base-consonant + U+093C (verified via `unicodedata.decomposition`),
#: which makes a literal precomposed character in source text a silent
#: trap - an editor/tool that normalizes non-ASCII text (confirmed
#: happening in this exact file during authoring) turns it into its own
#: decomposed form on save, with no visible difference and no error,
#: silently corrupting every consonant-combinatoric input list downstream
#: (`build_glyph_data.py`'s `"".join(...)` + `list(...)` calls would then
#: split each "consonant" into two separate list entries). `chr()` is
#: immune to this because it's evaluated in Python, never round-tripped
#: through a text editor's own normalization.
_HI_NUKTA_CONSONANT_CODEPOINTS = (0x958, 0x959, 0x95A, 0x95B, 0x95C, 0x95D, 0x95E)
NUKTA_CONSONANTS: tuple[str, ...] = tuple(chr(cp) for cp in _HI_NUKTA_CONSONANT_CODEPOINTS)

#: All 40 consonants build_glyph_data.py should treat identically for
#: standalone-ghost / consonant+matra / conjunct-sweep purposes - mirrors
#: _chars.py's CONSONANTS = REGULAR_CONSONANTS + SPECIAL_CONSONANTS pattern.
CONSONANTS: tuple[str, ...] = STANDARD_CONSONANTS + NUKTA_CONSONANTS

#: 10 core dependent vowel signs (matras), including ृ (vocalic R) -
#: promoted here from a rare tier per profile.md's RESOLVED #3, given its
#: real everyday frequency (कृष्ण, कृपा, कृत्रिम).
CORE_MATRAS: tuple[str, ...] = (*tuple("ािीुूेैोौ"), "ृ")

#: 2 modern loan matras (candra e/o vowel signs), pairing with LOAN_VOWELS.
LOAN_MATRAS: tuple[str, ...] = ("ॅ", "ॉ")

#: All in-scope core matras (RESOLVED, profile.md #5: loan matras in scope,
#: full generic treatment - same reasoning as INDEPENDENT_VOWELS above).
MATRAS: tuple[str, ...] = CORE_MATRAS + LOAN_MATRAS

#: 3 rare, Sanskrit-loanword-only matra signs (vocalic RR/L/LL).
RARE_MATRAS: tuple[str, ...] = ("ॄ", "ॢ", "ॣ")

#: Virama/halant - suppresses the inherent vowel; also the trigger for
#: every Devanagari conjunct-formation mechanism (reph, rakaar, half-forms,
#: akhand ligatures - see docs/languages/hi/font-report.md).
VIRAMA: str = "्"

#: Anusvara - nasalization before a following consonant.
ANUSVARA: str = "ं"

#: Candrabindu - nasalization of a vowel with no following consonant.
#: RESOLVED (profile.md #4): recorded in full, no normalization to/from
#: anusvara - phonemically distinct, not two spellings of one sound.
CANDRABINDU: str = "ँ"

#: Visarga - voiceless aspiration, rare outside direct Sanskrit borrowings.
VISARGA: str = "ः"

#: Nukta (U+093C) - combining loanword-sound diacritic attached directly to
#: a consonant (क + ़ = क़). RESOLVED (profile.md #1): needs NO recorded
#: stroke at all - synthesize it programmatically as a small dot (see
#: docs/languages/hi/labeling-worklist.md's "Synthetic strokes" group and
#: docs/LANGUAGE_ONBOARDING_AGENTS.md's "New composition primitives" note).
#: Its real font glyph outline is still needed (for the ghost/composition
#: geometry), just not a hand-traced ink stroke.
NUKTA: str = "़"

#: 10 Devanagari digits.
NUMERALS: tuple[str, ...] = tuple("०१२३४५६७८९")

#: Danda and double danda - Devanagari's own sentence/verse-end punctuation
#: (not the shared-Latin UNIVERSAL_CHARS set). RESOLVED (profile.md #2):
#: danda (।) gets one real recorded stroke; double danda (॥) is generated
#: from danda's own stroke, placed twice and offset by its real advance
#: width ("self-composition" - see labeling-worklist.md), not a separate
#: labeling-set entry. Both still need `clusters` ghost/ligature-detection
#: entries here, which is why both are listed.
NATIVE_PUNCTUATION: tuple[str, ...] = ("।", "॥")

#: Avagraha (vowel elision mark) and Om - real, in-scope marks with no
#: closer-fitting existing category (not a vowel, consonant, or matra).
#: New category found during Hindi's onboarding, generically supported by
#: build_glyph_data.py the same optional/gated way as CANDRABINDU/NUKTA/
#: NATIVE_PUNCTUATION were (see that module's docstring) - a no-op for
#: every language, including Malayalam, that doesn't define it.
RARE_MARKS: tuple[str, ...] = ("ऽ", "ॐ")
