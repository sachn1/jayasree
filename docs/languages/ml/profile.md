# Malayalam — Script Profile

> **Status: retrospective snapshot, not a proposal.** Unlike every other
> `docs/languages/<code>/profile.md` this pipeline produces, Malayalam is
> already fully onboarded, shipped, and verified - this document was
> written *after the fact* (2026-09-04), reconstructed from the actual
> implementation, as a reference point for calibrating future languages'
> Agent 1 profiles against a known-correct, already-shipped example. It is
> **not a living spec** and carries no sign-off gate of its own. The real
> source of truth is, and remains, `python/src/jayasree/_chars.py` (the
> character inventory), `js/src/glyph-data.json` (the font-verified
> composition data), and `js/src/stroke-data(.raw).json` (the actual
> recorded strokes) - if any of those ever change, this document does not
> update itself and should not be read as authoritative over the code. For
> the *mechanism* behind anything mentioned here (mark composition, the
> chillu-normalization runtime step, ligature/atom-set derivation), see
> `docs/ARCHITECTURE.md` - this document intentionally covers only
> Malayalam's own *linguistic facts*, not the script-agnostic engine that
> consumes them.

## Independent vowels

13 standard letters, standalone at word start:
അ ആ ഇ ഈ ഉ ഊ ഋ എ ഏ ഐ ഒ ഓ ഔ (`INDEPENDENT_VOWELS` in `_chars.py`).

**Sanskrit-loanword-only, rare, but shipped** (`RARE_VOWELS`): ൠ *(long
vocalic R)*, ഌ *(vocalic L)*, ൡ *(long vocalic L)* - unlike some of Hindi's
"open question, flagged for the human" rare-character calls, these were
included without qualification; Malayalam's own written tradition treats
them as part of the standard inventory taught alongside the 13 above, just
rare in everyday use.

## Consonants

**33 regular** (`REGULAR_CONSONANTS`), Sanskrit-derived, in traditional
articulation order: ക ഖ ഗ ഘ ങ, ച ഛ ജ ഝ ഞ, ട ഠ ഡ ഢ ണ, ത ഥ ദ ധ ന, പ ഫ ബ ഭ മ,
യ ര ല വ ശ ഷ സ ഹ.

**3 special** (`SPECIAL_CONSONANTS`) - Dravidian sounds with no Sanskrit
equivalent: ള *(retroflex la)*, ഴ *(zha, a sound largely unique to Tamil/
Malayalam)*, റ *(alveolar ra)*. `CONSONANTS = REGULAR_CONSONANTS +
SPECIAL_CONSONANTS` (36 total) is the combined tuple most of the pipeline
actually iterates.

**2 rare/archaic** (`RARE_CONSONANTS`, not part of the 36-member
`CONSONANTS` tuple - must be added explicitly by any caller that wants
them): ഩ *(alveolar na, U+0D29)*, ഺ *(alveolar ta, U+0D3A)* - appear in some
traditional texts, included in the shipped inventory for completeness
rather than excluded as archaic-only.

## Chillu letters

**6 bare word-final consonant forms** (no inherent vowel), `CHILLU` in
`_chars.py`: ൻ ർ ൽ ൾ ൺ ൿ *(chillu ka, U+0D7F)*.

This is Malayalam's single most Dravidian-specific structural feature, and
the one `docs/LANGUAGE_ONBOARDING_AGENTS.md` explicitly warns not to expect
an equivalent of in other scripts (confirmed true for Hindi - see
`docs/languages/hi/profile.md`'s `chillu_equivalent` note: Devanagari has
none, a bare consonant is just written with an explicit virama). Each
chillu has a legacy 3-codepoint spelling
(`consonant + ് (virama, U+0D4D) + ZWJ (U+200D)`), visually identical to
the atomic codepoint in every font, still produced by many keyboards/older
software. **The dual-encoding fact itself is stated here as the language
fact; the runtime normalization mechanism that reconciles it
(`normalizeChillus()`) is documented in `docs/ARCHITECTURE.md`'s "Chillu
letters" section** - read that, not this, for how it's actually handled.

## Matras (dependent vowel signs)

**12 core** (`MATRAS`): ാ ി ീ ു ൂ ൃ െ േ ൈ ൊ ോ ൌ.

**Compound/split vowel signs**: ൊ, ോ, and ൌ each have a canonical Unicode
NFD decomposition into a prefix+suffix pair - ൊ→െ+ാ, ോ→േ+ാ, ൌ→െ+ൗ. **ൈ is
the one exception**: no Unicode decomposition exists for it, and in Manjari
it renders as a single prefix-only glyph rather than two parts, so it's
recorded and treated as its own ordinary atom rather than decomposed. (The
decomposition *mechanism* - `SPLIT_VOWEL_PARTS`/`_SPLIT_VOWELS`, applied via
`applySequentialMarkStrokes` - is `docs/ARCHITECTURE.md`'s "Compound vowel
signs" section, not repeated here.)

**Au length mark** (`AU_LENGTH_MARK`, ൗ, U+0D57): a separate codepoint from
the au vowel sign ൌ (U+0D4C) above - used standalone or as ൌ's own suffix
component after decomposition. Same "two different codepoints, don't
conflate" caution the Hindi profile raises for its own loan-vowel/
loan-matra pairs (ऍ/ॅ, ऑ/ॉ).

**Sanskrit-loanword-only, rare, shipped** (`RARE_MATRAS`): ൄ *(vocalic RR
sign, U+0D44)*, ൢ *(vocalic L sign, U+0D62)*, ൣ *(vocalic LL sign, U+0D63)*
- same "included without a common/standard-usage filter" treatment as
`RARE_VOWELS` above.

**Fused-into-consonant-shape exceptions**: a handful of vowel signs (ു, ൂ,
ൃ) and the reduced la-form fuse into a shape unique to the specific
preceding consonant in real Manjari shaping and cannot be reconstructed
from the generic mark recipe - these need their own consonant-specific
recorded stroke rather than composing generically. (Full derivation:
`docs/ARCHITECTURE.md`'s "Compound vowel signs" section, last paragraph, and
`_build_marks()`'s docstring in `build_glyph_data.py`.) This is the
concrete, already-verified precedent Hindi's profile cites for its own open
question about ृ (vocalic R matra) possibly fusing per-consonant.

## Virama, nasalization, aspiration

- **Virama** (chandrakkala): ് (U+0D4D) - suppresses the inherent vowel;
  also the trigger for both chillu's legacy 3-codepoint spelling and every
  subjoined conjunct tail below.
- **Anusvara**: ം (U+0D02) - nasalization.
- **Visarga**: ഃ (U+0D03) - aspiration.

Malayalam draws no candrabindu-vs-anusvara distinction the way Hindi's
profile documents (`_chars.py` has no separate candrabindu constant) -
anusvara alone covers this territory in Malayalam orthography.

## Numerals

10 digits, ൦ ൧ ൨ ൩ ൪ ൫ ൬ ൭ ൮ ൯ (`NUMERALS`). As with Hindi's Devanagari
digits, Latin digits are also common in modern printed/typed Malayalam but
are `UNIVERSAL_CHARS`-shaped (script-independent, no ghost, no stroke), not
part of this category.

## Subjoined conjunct tails

**4 composable marks**, each a 2-codepoint `consonant-independent virama +
ya/va/la/ra` sequence, not a standalone `_chars.py` character but a
first-class entry in `glyph-data.json`'s `marks` table (23 entries total:
virama, all 12 core matras, 3 rare matras, the au-length mark, anusvara,
visarga, and these 4): ്യ, ്വ, ്ല, ്ര. These are the closest Malayalam
analogue to Hindi's "half-form" mechanism (`docs/languages/hi/profile.md`'s
conjunct hypotheses) - a productive, reusable prefix-mark recipe applying
across many base consonants, rather than a per-pair bespoke shape. (See
`docs/ARCHITECTURE.md`'s "The mark recipe" section for exactly how a
`{shift, prefix, suffix, trailingWidth}` recipe composes one of these onto
an arbitrary base - not repeated here.)

## True ligatures

**~108 conjunct clusters** (consonant+consonant, and longer consonant
chains) fuse into a single Manjari glyph unrelated in shape to their
component parts, and cannot be decomposed or generically composed - these
are recorded as their own atoms, the direct analogue of what Hindi's
profile calls "akhand ligatures" and currently leaves as an open,
font-unverified hypothesis (`क्ष`/`ज्ञ` "near-universal," others uncertain).
For Malayalam this question is already closed: the true set was found by
actually shaping every candidate cluster through HarfBuzz during
`build_glyph_data.py`'s run (`docs/ARCHITECTURE.md`'s Stage 1 section), not
guessed from written-tradition familiarity - the same exhaustive,
per-font-verified method Hindi's own Agent 2/3 stages are designed to
apply before trusting any curated list.

## The reduced atom set, in practice

`glyph-data.json` currently covers **2,052 total clusters** (every
standalone character, consonant+matra, and conjunct combination the font
can produce); of those, **297 have an actual hand-authored stroke**
(`stroke-data.raw.json`) - the reduced atom set `stroke-recorder.html`'s
dropdown defaults to. Everything else composes at request time from those
297 plus the 23-entry `marks` table, via `js/src/index.js`'s
`tryComposeStroke`/`resolveSegments` (script-agnostic engine, documented in
full in `docs/ARCHITECTURE.md` - not repeated here). These are the real,
current numbers as of this snapshot; `README.md`'s "Status" section is the
place to check if they've since moved (recording is ongoing, not frozen).

## Font

**Manjari** by Santhosh Thottingal & Swathanthra Malayalam Computing, SIL
Open Font License 1.1 (<https://smc.org.in/fonts/manjari>). Unlike Hindi's
`font-report.md`, no comparative candidate evaluation exists for
Malayalam's font choice in this repository's history - Manjari predates
this project's language-onboarding pipeline design and was simply the
project's starting choice. See `README.md`'s "License & credit" section and
`LICENSE-DATA` for the exact attribution terms this project already commits
to honoring.

## Why this document exists

Every other file under `docs/languages/` is a *pipeline artifact*: a
proposal an agent produced, gated on human sign-off, for a language not yet
shipped. This one is different on purpose - it exists so that `docs/
languages/hi/profile.md` (and Tamil's, Telugu's, ... whichever comes next)
has something to be compared against beyond just prose descriptions in
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s "Don't generalize from Malayalam"
section: a real, structured, same-shaped profile for the one language this
project has actually finished. If `_chars.py` or the generated data files
change after 2026-09-04, treat any mismatch with this document as this
document being stale, not the code being wrong - it is not regenerated or
kept in sync automatically, and nothing in the pipeline depends on it being
current the way `glyph-data.json`/`stroke-data.json` are depended on.

## Sources

Everything above is reconstructed from this repository's own already-
verified, already-shipped implementation - no external research, unlike
Hindi's profile:

- `python/src/jayasree/_chars.py` - the actual character inventory
- `docs/ARCHITECTURE.md` - composition mechanism, chillu normalization,
  compound-vowel decomposition, the ~108-ligature and reduced-atom-set
  figures' provenance
- `README.md` - "Status" section (atom/cluster counts) and "License &
  credit" section (Manjari's license/attribution terms)
- `js/src/glyph-data.json`, `js/src/stroke-data.raw.json` - spot-checked
  directly for this snapshot's exact counts (2,052 clusters, 23 marks, 297
  recorded atoms)
