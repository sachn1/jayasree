# Hindi (Devanagari) - onboarding record

The condensed record of Hindi's onboarding through
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s pipeline: what was decided, what the
numbers are, and what is still open. It is the format a later language's
record should follow. The long working reports (profile, font report,
shirorekha and composition-primitives reports, worklist) were folded into
this file; the originals are in git at commit `e7d7fa5`, e.g.
`git show e7d7fa5:docs/languages/hi/font-report.md`.

Files kept alongside this one: `reduced-atom-list.flat.txt` (the 183 atoms,
one per line - the `--simulate-atoms` input of `tools/coverage_report.js`).
The character inventory lives in `python/src/jayasree/_chars_hi.py`.

## Status

| Stage | Outcome |
|---|---|
| 1 Research | Agent 1 draft reviewed by the reviewer agent; the project owner resolved all open questions on 2026-09-04 (below). No single "approved" line was recorded for the profile as a whole. |
| 2 Font | **Noto Sans Devanagari** (static Regular), approved by the project owner 2026-09-06; supersedes Annapurna SIL. |
| 3 Atom set | **183 atoms**, derived against Noto; simulated coverage 100% (2443/2443). |
| 4 Recording | All 183 recorded by the owner (`js/src/stroke-data.hi.raw.json`). |
| 5 Process + verify | `stroke-data.hi.json`: 2782 clusters; real coverage 2443/2443, 0 outline fallbacks; strokes cleaned against the font (`jayasree.cleanup`). |
| 6 Inspect | owner has checked the letters and half-forms in the demo. |

## Scope decisions (project owner, 2026-09-04)

Governing principle: **coverage is bounded by the font, not by linguistic
minimalism** - animate whatever the user types, as long as the chosen font
supports it.

1. **Nukta consonants** (क़ ख़ ग़ ज़ ड़ ढ़ फ़): in scope wherever the font renders
   them. Nukta (़) itself needs **no human stroke** - a synthetic dot (the
   "synthetic strokes" primitive). All 7 have a real canonical NFD
   decomposition (base + U+093C) and the font shapes both spellings to one
   glyph, so the duality is handled by `legacyEncodings` (the same mechanism
   as Malayalam's chillus).
2. **Danda (।)**: one real recorded stroke. **Double danda (॥)**: intended to
   self-compose from danda, but it is its own atomic codepoint (no
   decomposition), so the runtime's character-split never yields two dandas;
   it is recorded directly instead (Group C).
3. **ृ (vocalic R matra)**: core matra set, not rare.
4. **Candrabindu (ँ) and anusvara (ं)**: both recorded, no normalization
   (phonemically distinct).
5. **Loan vowels/matras** (ऍ ऑ / ॅ ॉ): in scope.

**Excluded** (Sanskrit/Vedic or other-language only, reserved for a future
profile): Vedic accents U+0951-0954 and the Devanagari Extended-A block
U+A8E0-A8FF; Unicode 7.0 letters for Marwari/Kashmiri/Konkani/Sindhi/Dogri
(U+0972-097F) and U+093A/093B.

## Font decision

Original pick: **Annapurna SIL 3.000** (OFL 1.1; 120/120 required atoms, zero
`.notdef`; other candidates Noto Sans Devanagari and Mukta, all OFL). A
re-evaluation then added a 4th selection criterion, **(d) low stroke-width
contrast / monoline**, because gradient-ascent centering
(`docs/CENTERING_EXPERIMENTS.md`) is unreliable at corners and junctions,
which a calligraphic font multiplies. Measured stroke-width coefficient of
variation: **Noto 0.074** (lowest of 8 monoline candidates), Yantramanav
0.119, **Annapurna 0.231** (about 3x worse). Hind, Palanquin, Poppins,
Rajdhani, Sarala and Baloo 2 all failed the composability criterion (no
generic half-form; every pair bespoke); Mukta failed it earlier. Noto is the
only candidate both the most monoline and composable.

Noto ships as a variable font; the vendored file is a static instance
(`fonttools varLib.instancer ... wght=400 wdth=100`), verified byte-identical
in shaping to the variable source across all 119 atom tests and 9 spot-check
conjuncts. unitsPerEm/ascent/descent 1000/896/-408, 1117 glyphs. It lives at
`python/tests/fixtures/NotoSansDevanagari-Regular.ttf` (+ OFL text) and is
`languages.py`'s `hindi` `default_font`. Annapurna's SHA-256 was `a2bba202...0977`.

Cost of the switch, stated plainly: the true-ligature set is font-specific.
Under Noto, 15 pairs fuse that did not under Annapurna and 9 stopped fusing,
so the atom set went **174 -> 183**.

## The 183-atom set

| Group | Count | Contents |
|---|---|---|
| A - standalone | 89 | 13 independent vowels (incl. loan ऍ ऑ); 3 rare vowels ऌ ॠ ॡ; 40 consonants (33 + 7 nukta); 10 numerals; danda; 12 matras (incl. ृ ॅ ॉ); 3 rare matras ॄ ॢ ॣ; ् ं ः ँ; ऽ ॐ; the rakaar ghost ्र |
| B - synthetic | 1 | nukta ़ (a generated dot, no tracing) |
| C - recorded directly | 1 | double danda ॥ |
| D - ligatures / exceptions | 53 | 47 true akhand ligatures: क्ष ङ्क ङ्ख ङ्ग ङ्घ ङ्म ङ्य च्छ छ्य छ्व ज्ञ ट्ट ट्ठ ट्य ठ्ठ ठ्य ड्ड ड्ढ ड्य ढ्ढ ढ्य त्त द्ग द्घ द्द द्ध द्ब द्भ द्म द्य द्व न्न प्न ब्ध व्य श्च श्न श्ल श्व ष्ट ष्ठ ह्ण ह्न ह्म ह्य ह्ल ह्व; plus 6 half-form exceptions छ्र ज्ज ज़्ज न्थ न्ध म्भ (their base glyph differs from that consonant's majority half-form) |
| E - contextual forms | 39 | 38 half-form atoms (one per consonant except र and द; keyed by trigger e.g. "क्") + 1 reph hook "र्" |

Under Noto, 9 pairs that fused under Annapurna (क्क क्त ङ्ङ ङ्ह च्च प्त म्ल
ल्ल स्न) now fall to a generic half-form or explicit-halant rendering, and
द has no generic half-form at all (every pair fuses or falls through to 3
glyphs). The reph hook has no exceptions. Half-form/reph ghosts cannot be
sourced by shaping the trigger alone; they are extracted from an
already-shaped conjunct cluster. `build_glyph_data.py` writes the 183 into
`knownAtoms`, which the recorder treats as default-visible atoms (earlier,
Group D's 53 were invisible in its dropdown).

## The headline finding: contextual forms

Malayalam's reduction rests on "a base's recorded stroke + a trailing mark's
recipe". A 40x40 sweep of every `consonant + ् + consonant` pair (Noto) shows
Devanagari does not fit:

| Category | Pairs | Chars/glyphs | Composable? |
|---|---|---|---|
| Reph (र first) | 40 | 3/2, glyph order reversed | needs a new primitive |
| Rakaar (र second, fused) | 31 | 3/1 | yes - `्र` recorded once as a mark |
| True akhand ligatures | 47 | 3/1 | no - recorded directly (Group D) |
| Generic half-form + full | 1195 | 3/2 | needs a new primitive |
| Explicit-halant fallthrough | 287 | 3/3 | yes - per-character fallback |

The new primitive is `tryComposeContextualForm` / `compose_contextual_form`
driven by `glyphData.contextualForms` (see `docs/ARCHITECTURE.md`). The
half-form exception list is `_HI_HALFFORM_EXCLUDED_PAIRS` in
`tools/build_glyph_data.py` (Annapurna had 2 pairs, Noto has 6).

## Shirorekha (headline) - decided, not yet built

Raised by the owner during font review. A composed word stitched from
per-character hand-traced headline segments would be uneven, so the agreed
approach (2026-09-04) is a **synthetic word-level stroke**: tracers skip the
top line; the renderer draws it programmatically over the word's width.

- **One constant is safe per font**, and it is per-font data, never copied
  across a swap. Annapurna: y -1320..-1188 (132 units, 2048 upm), identical
  across all 55 clean glyphs. **Noto: y -622..-551 (71 units, 7.1% of the em),
  top edge at font_y 622 (69.4% of ascent)**, from 4 splittable glyphs plus a
  top-edge check over 51.
- **Six letters have a real gap in the headline**: थ ध भ श and the vowels अ आ
  (gap is a centered 42-68% of the glyph's advance width - an open loop at
  top-center). The same six sit 10 units higher (y -632 vs -622).
- **Revised design:** the headline is **N sub-strokes per word**, split at
  those letters' gap x-ranges (scaled by rendered width), all drawn **last**,
  after every character's and matra's own strokes - never interleaved.
- Not checked: matras, conjunct pairs and nukta consonants for these gaps, and
  nobody has yet visually confirmed a rendered word with a gap letter. Needs a
  spot-check on at least one word each for थ ध भ श अ आ.
- The pattern generalizes to other Devanagari-based scripts; Bengali's
  headline convention is less consistent, worth checking then.

## Corrections the mechanical pass found

1. `chars.json`'s `loan_vowels` had the matra codepoints ॅ/ॉ instead of the
   independent letters ऍ/ऑ (a copy-paste bug).
2. The profile overstated nukta's encoding ambiguity; all 7 decompose
   canonically (see decision 1).
3. The font report's Annapurna non-rakaar fusion count had an arithmetic
   error (irrelevant to Noto's independently re-derived 47).

## Still open

- Constant pen speed (the shared ease-in/out is slow-fast-slow); see `docs/ROADMAP.md`.
- Implement and verify the shirorekha design above.
- The profile has no recorded final sign-off (see Status).

## Reproducing

```bash
cd python && poetry run python ../tools/build_glyph_data.py --lang hindi   # glyph-data.hi.json
node tools/coverage_report.js --simulate-atoms docs/languages/hi/reduced-atom-list.flat.txt \
                              --glyph-data js/src/glyph-data.hi.json       # 183 atoms -> 100%
```

## Sources

Unicode Devanagari block (compart.com); Microsoft's "Developing OpenType
Fonts for Devanagari Script" (the shaping model: akhn, rphf, rkrf, blwf,
half, pref, vatu, cjct); Richard Ishida's Hindi orthography notes
(r12a.github.io/scripts/deva/hi.html); Wikipedia's Devanagari and Devanagari
(Unicode block); nukta usage cross-checked against LangLex and aashaan.in (no
single authoritative list exists). Fonts: Annapurna SIL
(github.com/silnrsi/font-annapurna, v3.000), Noto Sans Devanagari
(github.com/notofonts/devanagari), Mukta (github.com/EkType/Mukta), all OFL 1.1.
