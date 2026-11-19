# Hindi (Devanagari) — Labeling Worklist

Agent 3's output from `docs/LANGUAGE_ONBOARDING_AGENTS.md` (Agent 3
section) — driven mechanically against Agent 1's approved profile
(`docs/languages/hi/profile.md`, `chars.json`) and Agent 2's approved font
(`docs/languages/hi/font-report.md`, **Noto Sans Devanagari (static
Regular instance)**, vendored at
`python/tests/fixtures/NotoSansDevanagari-Regular.ttf`). This is the
human-facing deliverable: what to actually trace, in what order, and why
the count is what it is — including a real, evidence-backed complication
Devanagari's own conjunct-formation mechanics raise that Malayalam's
onboarding never had to solve (see "The headline finding" below — this
doc's single most important section for whoever reads it next).

> **2026-09-06 font-swap update**: this worklist originally ran against
> **Annapurna SIL** (41 true akhand ligatures, 2 half-form exceptions, 174
> total atoms, 100% simulated coverage). `font-report.md`'s "Re-evaluation"
> section replaced Annapurna SIL with **Noto Sans Devanagari** (lower
> stroke-width contrast, better suited to this project's
> centering/straightening algorithm — see that report for the full
> reasoning) — a real, human-approved font-choice decision, not something
> this pass second-guesses. Every number below was re-derived from scratch
> against the regenerated `js/src/glyph-data.hi.json` (built from Noto),
> per `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s own instruction that the
> labeling set is font-specific and must be re-verified, not carried over,
> whenever the font changes. **The reduced atom set grew from 174 to
> 183** — the mechanism (marks table + contextual-form primitives) is
> unchanged and still achieves 100% simulated coverage; only the
> font-specific *data* (which pairs fuse, which half-forms have
> exceptions) differs. See `docs/languages/hi/composition-primitives-report.md`'s
> "Re-verification (2026-09-06)" section for the detailed per-consonant
> findings behind these new numbers.

**Method, in one line**: `python tools/build_glyph_data.py --lang hindi`
was run against the approved font to produce `js/src/glyph-data.hi.json`
(2443 clusters, 21 marks); the reduced atom set below was derived from
that file's own `marks` table plus an exhaustive, code-verified sweep of
every two-consonant conjunct pair — never guessed or copied from
Malayalam's category names, per the plan's "Don't generalize from
Malayalam." Every count in this document is reproducible by re-running the
commands cited alongside it.

> **2026-10-03 recorder-visibility fix**: Group D's 53 true akhand
> ligatures/half-form exceptions used to be invisible in
> `tools/stroke-recorder.html`'s default dropdown — `isAtom()` only
> auto-shows single codepoints and `marks{}`/`contextualForms{}` keys, so
> these 53 only appeared after being typed, one at a time, into "+ Add
> custom cluster" (no bulk-add existed). Fixed properly instead of
> papering over it with a bulk-add button: `tools/build_glyph_data.py`'s
> `_runtime_quirks()` (its `lang.code == "hi"` block) now also computes and
> writes a `knownAtoms` list (same mechanical sweep this doc's Group D
> numbers already came from, reused rather than re-derived by hand), and
> the public, language-generic `tools/stroke-recorder.js` now treats
> `knownAtoms` membership as another reason a cluster is an atom by
> default - same tier as `marks`/`contextualForms`. All 183 atoms now show
> by default; no manual add/remember-the-list step needed. Re-run
> `make build-glyph-data PROJECT_LANG=hindi && make build-recorder
> PROJECT_LANG=hindi` to pick this up in an already-checked-out standalone
> recorder.

## Corrections found while running this pass (original, Annapurna SIL — still valid)

Per this pipeline's design principle 3 ("verification is structural, not
self-reported"), running the actual pipeline against real data surfaced
concrete bugs/refinements in earlier, already-"approved" documents. None
of these are scope changes — all are corrections to claims that turned out
to be factually wrong when checked mechanically. These predate the font
swap and are unaffected by it (they're about `chars.json`/`profile.md`,
not font-specific data):

1. **`chars.json`'s `loan_vowels` category had the wrong codepoints** — it
   listed the matra signs ॅ/ॉ (U+0945/0949, duplicating `loan_matras`)
   instead of the independent-vowel letters ऍ/ऑ (U+090D/0911) that its own
   note and `profile.md`'s prose both correctly describe. Fixed directly
   in `chars.json` (the structured, machine-readable source `_chars_hi.py`
   is promoted from) — a mechanical copy-paste bug, not a judgment call.
2. **Nukta's encoding-duality claim was overstated.** `profile.md` hedged
   that "some of U+0958–095F are not canonical-equivalent to their
   decomposed sequence." Checked directly via
   `unicodedata.decomposition()`: all 7 of Hindi's in-scope nukta
   consonants (U+0958–095E) *do* have a real Unicode canonical NFD
   decomposition into base-consonant + U+093C, and this font shapes both
   spellings to the identical single glyph (verified via HarfBuzz). This
   is good news — it means the encoding duality is fully solvable with
   existing machinery (see "Nukta" below), not a genuine ambiguity.
3. **`font-report.md`'s non-rakaar akhand-fusion count has an internal
   arithmetic error** (in its original, Annapurna-SIL-specific pass — see
   that report for details). Not relevant to Noto's own count below,
   which was independently re-derived from scratch against
   `glyph-data.hi.json`, not copied from any prose figure.

None of these change any prior human sign-off decision (scope, font
choice) — they're the kind of thing Agent 2/3's mechanical verification
exists to catch before a human spends real tracing time on their strength.

## The headline finding: Devanagari conjunct composition needs a primitive Malayalam's pipeline never needed

This is the load-bearing result of this pass, and the reason the atom
count below is much larger than Malayalam's ~297 despite Hindi's own
character inventory being comparable in size. Read this before the
tables — it explains every subsequent number. (This finding's *mechanism*
is font-independent; the *specific numbers* below are Noto Sans
Devanagari's, re-derived fresh, not carried over from the original
Annapurna SIL pass.)

Malayalam's whole atom-reduction strategy rests on one mechanism:
`tryComposeStroke`/`tryComposeFromCharacters` in `js/src/index.js` compose
a cluster from **a base's own recorded stroke plus a trailing mark's
recipe** (`glyphData.marks`), where the mark is either a suffix diacritic
(matra, virama, subjoined ്യ/്വ/്ല/്ര) or, for the character-splitting
fallback, a cluster whose character count equals its glyph count.

**Devanagari's own OpenType conjunct-formation model doesn't fit either
shape**, verified directly against the regenerated `glyph-data.hi.json`
(Noto Sans Devanagari): a 40×40 sweep of every `<consonant>+्+<consonant>`
pair (including the 7 nukta consonants) shows:

| Category | Count | Chars | Glyphs | Composable today? |
|---|---|---|---|---|
| Reph (र first) | 40 | 3 | 2 | **No** — chars≠glyphs, and the glyph *order* is reversed (2nd char's glyph comes first) |
| Rakaar/vattu (र second, fused) | 31 | 3 | 1 | **Yes**, as of this pass — see "Rakaar" below |
| True akhand ligatures (other fused) | 47 | 3 | 1 | No — genuinely unique glyphs, same as any true ligature |
| Generic half-form + full (chars≠glyphs) | 1195 | 3 | 2 | **No** — chars≠glyphs |
| Explicit-halant fallthrough (chars==glyphs) | 287 | 3 | 3 | **Yes** — already generically composable via the existing per-character fallback, no new primitive needed |

(1600 = 40×40 total, all four+one categories above.)

The `chars≠glyphs` rows are the crux: `tryComposeFromCharacters`'s own
gate (`clusterEntry.glyphs.length !== chars.length`) exists specifically
to bail out when a character doesn't map 1:1 to a glyph — and for
Devanagari, a virama between two consonants **almost never produces its
own glyph** unless the font falls all the way through to the fully
decomposed explicit-halant rendering (287 of 1600 pairs, this font) — the
virama otherwise either triggers a fused ligature (1 glyph) or a
half-form substitution (2 glyphs, but for 3 characters). Malayalam never
hit this because its own conjunct-formation marks (്യ/്വ/്ല/്ര) are
trailing, generic, and reduce a *following* consonant to a fixed tail —
Devanagari's half-form mechanism instead substitutes the *first*
consonant's own shape, and reph reorders the *first* consonant's glyph to
the very end of the whole syllable. Neither is a "trailing mark," so
neither fits `marks{}`'s model without a real runtime extension.

**What this pass fixed vs. what it's flagging, not fixing:**

- **Rakaar — fixed**, using existing precedent exactly (no new runtime
  code). Shaping "्र" alone against a dotted-circle placeholder (the same
  technique `_build_marks()` already uses for every matra) produces a
  single, dedicated, reusable glyph — structurally identical to
  Malayalam's own `virama + "ര"` quirk, and font-independent (rakaar's
  own standalone shaping works the same way regardless of font, unlike
  half-forms/reph — see `composition-primitives-report.md`§3).
  `tools/build_glyph_data.py`'s `lang.code == "hi"`-gated block records
  `्र` once and adds it to `_composable_marks()`, so all 31 rakaar pairs
  compose generically via the existing `tryComposeStroke` — verified in
  the coverage numbers below (rakaar pairs are *not* in the direct-atom
  list; only the one `्र` ghost is).
- **Nukta's encoding duality — fixed**, reusing `legacyEncodings`/
  `normalizeChillus` (already fully generic). `build_glyph_data.py`
  writes a `hi`-gated `legacyEncodings` table mapping each of the 7
  decomposed `base+़` sequences to its precomposed atomic codepoint,
  exactly mirroring Malayalam's own chillu-spelling normalization —
  font-independent (confirmed unchanged after the font swap:
  `legacyEncodings` still maps all 7 nukta consonants identically).
- **Half-forms and reph — fixed**, via `tryComposeContextualForm`/
  `compose_contextual_form` (built after the original Annapurna SIL
  pass — see `js/src/index.js`, `python/src/jayasree/stroke_compose.py`).
  Re-verified against Noto in `composition-primitives-report.md`'s
  "Re-verification (2026-09-06)" section — the primitive itself still
  applies; the specific exception-pair list it needs
  (`_HI_HALFFORM_EXCLUDED_PAIRS`) changed from Annapurna's 2 pairs to
  Noto's 6.

### How this was checked

Reproducible directly against the regenerated `glyph-data.hi.json`:

```python
import json
data = json.load(open("js/src/glyph-data.hi.json", encoding="utf-8"))
clusters = data["clusters"]
consonants = list(__import__("jayasree._chars_hi", fromlist=["CONSONANTS"]).CONSONANTS)
virama = "्"
for c1 in consonants:
    for c2 in consonants:
        entry = clusters[c1 + virama + c2]
        n_chars, n_glyphs = 3, len(entry["glyphs"])
        # c1 == "र" -> reph; n_glyphs == 1 and c2 == "र" -> rakaar;
        # n_glyphs == 1 otherwise -> true fusion; n_glyphs == 2 -> half-form;
        # n_glyphs == 3 -> explicit-halant fallthrough (already composable)
```

## Reduced atom set

Every number below is what `docs/languages/hi/reduced-atom-list.txt`
(committed alongside this doc, grouped/commented) actually contains — not
a summary written independently of it. The flat, comment-free version
(`reduced-atom-list.flat.txt`) is the literal `--simulate-atoms` input used
for the coverage audit further down.

### Group A — standalone atoms (89 total, highest priority)

Trace these first: every other composition depends on these existing
before it can even be spot-checked, exactly as
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s priority-ordering guidance says.
Unaffected by the font swap (this group comes from `chars.json`'s
inventory, not font-specific shaping data).

| Subgroup | Count | Contents |
|---|---|---|
| Independent vowels (incl. 2 loan) | 13 | अ आ इ ई उ ऊ ऋ ए ऐ ओ औ ऍ ऑ |
| Rare (Sanskrit-loanword) vowels | 3 | ऌ ॠ ॡ |
| Consonants (incl. 7 nukta) | 40 | क–ह (33) + क़ ख़ ग़ ज़ ड़ ढ़ फ़ (7) |
| Numerals | 10 | ० – ९ |
| Danda | 1 | । |
| Matras (incl. 2 loan, incl. ृ) | 12 | ा ि ी ु ू े ै ो ौ ृ ॅ ॉ |
| Rare matras | 3 | ॄ ॢ ॣ |
| Virama / anusvara / visarga / candrabindu | 4 | ् ं ः ँ |
| Rare marks | 2 | ऽ (avagraha) ॐ (Om) |
| Rakaar mark ghost | 1 | ्र — see "Rakaar" above; give the recorder a real reference the same way Malayalam's ്ര does |

**All 89 need real human-traced strokes** except nukta (Group B, below) —
none of these are synthesizable or self-composable; they're this script's
actual, distinct letterforms.

### Group B — synthetic (1 total, no tracing)

- **Nukta (़, U+093C)** — a small dot. RESOLVED in `profile.md`: no
  human-traced recording needed at all, only the real font glyph outline
  (already in `glyph-data.hi.json`'s `clusters`) for ghost/composition
  geometry. Whoever runs Phase 2's recording session should synthesize a
  small filled-circle stroke and write it directly into
  `stroke-data.raw.json` under `"़"` — the composition code doesn't care
  whether a stroke was traced or generated, only that
  `STROKE_LIBRARY["़"].strokes` is non-empty.

### Group C — self-composition target, recorded directly for now (1 total)

- **Double danda (॥, U+0965)** — `profile.md`'s resolution #2 says this
  self-composes from danda's own stroke, "not a separate labeling-set
  entry." **That claim doesn't hold under the current runtime**: U+0965
  has no Unicode decomposition — it's its own atomic codepoint, not a
  2-character "।।" sequence, so `tryComposeFromCharacters`'s `[...cluster]`
  character-split never produces two dandas to reuse. Pragmatically cheap
  to just record directly (it's one simple shape) — included here as its
  own atom rather than blocking on a new primitive for a single character.
  Font-independent (Unicode encoding fact, unaffected by the font swap).

### Group D — true ligatures and half-form exceptions, direct recording (53 total, up from Annapurna's 43)

| Subgroup | Count | Why it's here |
|---|---|---|
| True akhand ligatures | 47 (was 41) | Genuinely unique fused glyphs — always need direct recording, primitive or not (same as Malayalam's true ligatures). क्ष ङ्क ङ्ख ङ्ग ङ्घ ङ्म ङ्य च्छ छ्य छ्व ज्ञ ट्ट ट्ठ ट्य ठ्ठ ठ्य ड्ड ड्ढ ड्य ढ्ढ ढ्य त्त द्ग द्घ द्द द्ध द्ब द्भ द्म द्य द्व न्न प्न ब्ध व्य श्च श्न श्ल श्व ष्ट ष्ठ ह्ण ह्न ह्म ह्य ह्ल ह्व — 32 of these 47 are shared with Annapurna's own 41-pair list; **9 pairs that fused under Annapurna don't fuse under Noto** (क्क, क्त, ङ्ङ, ङ्ह, च्च, प्त, म्ल, ल्ल, स्न — each instead resolves to a generic half-form or explicit-halant fallthrough under Noto, already composable without direct recording) and **15 pairs fuse under Noto that didn't under Annapurna** (ङ्म, च्छ, छ्व, ड्ढ, ढ्ढ, द्ग, द्घ, द्ब, द्भ, प्न, ब्ध, व्य, श्न, श्ल, ह्ण) — see `composition-primitives-report.md` for the exact per-font sweep; the true akhand-fusion set is font-specific and must be re-swept per font, not hand-curated) |
| Half-form exceptions | 6 (was 2) | छ्र, ज्ज, ज़्ज, न्थ, न्ध, म्भ — verified (`composition-primitives-report.md`'s "Re-verification" §1) to shape as a distinct 2-glyph pair whose base-consonant glyph differs from that consonant's own majority half-form shape, so they're excluded from the generic half-form atom's derivation and recorded directly instead, same as any true ligature. **Different pairs than Annapurna's** (ड़्य, ढ़्य — which turn out to be plain 3-glyph fallthroughs under Noto, needing no exclusion at all) |

### Group E — contextual-form atoms (39 total, down from Annapurna's 40)

The half-form shapes and reph hook Group D used to gate on building a
primitive for — real, recordable atoms in their own right, each covering
many Group D pairs generically:

| Subgroup | Count | Contents |
|---|---|---|
| Half-form atoms | 38 (was 39) | One per consonant except र **and except द** — द has no generic half-form under Noto at all (every one of its pairs is either a true fusion, already in Group D, or a 3-glyph fallthrough that's already generically composable — see `composition-primitives-report.md`§1). Ghost sourced from an existing conjunct cluster's own glyph (see that report's §3 for why *not* standalone shaping), keyed by the 2-character trigger (e.g. "क्") |
| Reph hook atom | 1 | The small hook र्+consonant renders as, detached from its own typed position — keyed "र्" |

**Every one of these 39 needs a real human-traced stroke** — they're
genuinely distinct letterforms this font actually renders, verified
identical across every non-excluded partner consonant
(`composition-primitives-report.md`'s "Re-verification" §1–2), just never
individually recorded before. Give the recorder a real reference ghost the
same way rakaar's does — sourced from `glyphData.contextualForms[trigger].ghost`,
not `clusters` (a real `clusters` entry for e.g. "क्" would make real
word-final text ending in "क्" incorrectly render as the mid-conjunct
half-form instead of the linguistically correct explicit-halant form it
already gets today via virama's own pre-existing mark).

## Coverage audit (pre-recording, simulated)

Per the plan's coverage-audit gate — run against the *exact* runtime
composition code (`tryComposeStroke`/`tryComposeContextualForm`/
`tryComposeFromCharacters`), not a reimplementation:

```
node tools/coverage_report.js --simulate-atoms docs/languages/hi/reduced-atom-list.flat.txt --glyph-data js/src/glyph-data.hi.json
```

```
Coverage report (simulated) - js/src/glyph-data.hi.json
  seeded 183 simulated atoms
  2443 total clusters
  144 direct, 2299 composed, 0 fallback
  coverage: 2443/2443 (100.0%)
```

(Saved verbatim at `docs/languages/hi/coverage-report-pre-recording.txt`.)

**100% — every one of the 2443 clusters `glyph-data.hi.json` defines
resolves to a direct or composed stroke**, now from a **183-atom set**
(up from Annapurna's 174, down from a naive per-cluster count in the
thousands) — the contextual-form primitive closes exactly the gap "The
headline finding" identifies, without any `resolveSegments`/glyph-level
change at all.

183 = 89 (Group A) + 1 (Group B, nukta — included in the atom file purely
so the coverage tool's stub-stroke mechanism can exercise its composition
path; the *real* deliverable is a synthesized stroke, not a traced one) +
1 (Group C) + 53 (Group D) + 39 (Group E).

Post-recording, once real strokes exist, run the identical check against
`js/src/stroke-data.hi.raw.json` (`--stroke-data` instead of
`--simulate-atoms`) — this is the standing gate, not a one-time check.
`js/src/stroke-data.hi.raw.json`/`stroke-data.hi.json` are still both
empty (`{}`) — no strokes have been traced against either font yet, so
there is nothing to re-trace or invalidate from the font swap.

## What's already committed alongside this doc

- `js/src/glyph-data.hi.json` — regenerated via
  `python tools/build_glyph_data.py --lang hindi` against
  **Noto Sans Devanagari**, 2443 clusters, 21 marks (`्र` included), 39
  `contextualForms` entries (38 half-form + 1 reph).
- `js/src/stroke-data.hi.raw.json` / `js/src/stroke-data.hi.json` — both
  still `{}` (empty) — Phase 2's recording session starts from here,
  against the new font's ghosts.
- `docs/languages/hi/reduced-atom-list.txt` (grouped, commented) and
  `.flat.txt` (the literal `--simulate-atoms` input) — regenerated for
  Noto (183 atoms, up from 174).
- `docs/languages/hi/coverage-report-pre-recording.txt` — regenerated
  (183 seeded atoms, 100.0% coverage).
- `docs/languages/hi/composition-primitives-report.md` — re-verified
  against Noto, with the original Annapurna SIL pass kept for the
  historical record.
- `docs/languages/hi/shirorekha-report.md` — re-verified against Noto
  (a real font-construction difference found: Noto mostly fuses the
  headline into each glyph's main contour rather than keeping it as a
  separate subpath, unlike Annapurna — but the same "safe to use one
  constant" conclusion holds, now at `y=[-622,-551]`/1000 unitsPerEm
  instead of Annapurna's `y=[-1320,-1188]`/2048 unitsPerEm).
- `python/src/jayasree/_chars_hi.py` — unchanged (font-independent).
- `python/src/jayasree/languages.py` — `"hindi"`'s `default_font` updated
  to `python/tests/fixtures/NotoSansDevanagari-Regular.ttf`.
- `tools/build_glyph_data.py`'s `_HI_HALFFORM_EXCLUDED_PAIRS` — updated
  to Noto's real 6 exception pairs (replacing Annapurna's 2).

## Using the stroke recorder

`tools/stroke-recorder.html` works against `glyph-data.hi.json` with no
Hindi-specific logic hardcoded into it (its "reduced set" filter and the
shirorekha banner are both derived purely from whatever `marks{}`/
`meta.recorderNote` the loaded glyph-data itself defines). Drop
`js/src/glyph-data.hi.json` onto it (or use its file picker) to start
tracing — verified working against the regenerated (Noto) file.

`tools/build_standalone_recorder.py --lang hindi` regenerates
`tools/stroke-recorder-standalone.hi.html` against the new
`glyph-data.hi.json`/`stroke-data.hi.raw.json` pair.

## Review gate

Per the plan's Agent 3 review gate: this worklist and a spot-check sample
of `glyph-data.hi.json`'s ghost outlines (loadable via
`tools/stroke-recorder.html`) need a human who reads/writes Devanagari to
confirm the ghosts look right before Group A recording starts — this is a
fresh spot-check obligation now that the font itself has changed, even
though no strokes have been recorded yet (so there's nothing to
invalidate, only a first-time check to do against the new ghosts).
