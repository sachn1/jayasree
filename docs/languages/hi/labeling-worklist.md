# Hindi (Devanagari) — Labeling Worklist

Agent 3's output from `docs/LANGUAGE_ONBOARDING_AGENTS.md` (Agent 3
section) — driven mechanically against Agent 1's approved profile
(`docs/languages/hi/profile.md`, `chars.json`) and Agent 2's approved font
(`docs/languages/hi/font-report.md`, Annapurna SIL 3.000, vendored at
`python/tests/fixtures/AnnapurnaSIL-Regular.ttf`). This is the human-facing
deliverable: what to actually trace, in what order, and why the count is
what it is — including a real, evidence-backed complication Devanagari's
own conjunct-formation mechanics raise that Malayalam's onboarding never
had to solve (see "The headline finding" below — this doc's single most
important section for whoever reads it next).

**Method, in one line**: `python tools/build_glyph_data.py --lang hindi`
was run against the approved font to produce `js/src/glyph-data.hi.json`
(2443 clusters, 21 marks); the reduced atom set below was derived from
that file's own `marks` table plus an exhaustive, code-verified sweep of
every two-consonant conjunct pair — never guessed or copied from
Malayalam's category names, per the plan's "Don't generalize from
Malayalam." Every count in this document is reproducible by re-running the
commands cited alongside it.

## Corrections found while running this pass

Per this pipeline's design principle 3 ("verification is structural, not
self-reported"), running the actual pipeline against real data surfaced
concrete bugs/refinements in earlier, already-"approved" documents. None
of these are scope changes — all are corrections to claims that turned out
to be factually wrong when checked mechanically:

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
   arithmetic error.** It states "the remaining 19 pairs are genuine
   non-rakaar, non-reph single-glyph fusions" but its own code block lists
   **39** items, and a fresh exhaustive 33×33 sweep against the same
   committed font (reproduced independently for this pass, see
   "True akhand ligatures" below) finds **41** (39 plus ट्ठ and ड्ड, absent
   from font-report's printed list) once the full 40×40 sweep, including
   the 7 nukta consonants, confirms no *additional* fusions come from
   them. `font-report.md`'s named high-confidence examples (क्ष, ज्ञ, त्त)
   and its श्र-is-really-rakaar correction are both still accurate — only
   the "19" figure and the printed list's completeness were off.

None of these change any prior human sign-off decision (scope, font
choice) — they're the kind of thing Agent 2/3's mechanical verification
exists to catch before a human spends real tracing time on their strength.

## The headline finding: Devanagari conjunct composition needs a primitive Malayalam's pipeline never needed

This is the load-bearing result of this pass, and the reason the atom
count below is much larger than Malayalam's ~297 despite Hindi's own
character inventory being comparable in size. Read this before the
tables — it explains every subsequent number.

Malayalam's whole atom-reduction strategy rests on one mechanism:
`tryComposeStroke`/`tryComposeFromCharacters` in `js/src/index.js` compose
a cluster from **a base's own recorded stroke plus a trailing mark's
recipe** (`glyphData.marks`), where the mark is either a suffix diacritic
(matra, virama, subjoined ്യ/്വ/്ല/്ര) or, for the character-splitting
fallback, a cluster whose character count equals its glyph count.

**Devanagari's own OpenType conjunct-formation model doesn't fit either
shape**, verified directly against the committed `glyph-data.hi.json` (not
asserted from the font-report's prose — this pass re-derived it from
scratch): a 33×33 sweep of every `<consonant>+्+<consonant>` pair (using
this font's real shaped glyph counts, reproducible via the snippet in
"How this was checked" below) shows:

| Category | Count | Chars | Glyphs | Composable today? |
|---|---|---|---|---|
| Reph (र first) | 40 | 3 | 2 | **No** — chars≠glyphs, and the glyph *order* is reversed (2nd char's glyph comes first) |
| Rakaar/vattu (र second, fused) | 39 | 3 | 1 | **Yes**, as of this pass — see "Rakaar" below |
| True akhand ligatures (other fused) | 41 | 3 | 1 | No — genuinely unique glyphs, same as any true ligature |
| Generic half-form + full (everything else) | 1480 | 3 | 2 | **No** — chars≠glyphs |

(Counts are 40×40=1600 total, including the 7 nukta consonants — not
33×33=1089 as `font-report.md`'s own sweep used; extending to all 40
changes only reph 33→40 and rakaar 32→39, confirming no *additional*
akhand fusions come from the nukta consonants specifically.)

The `chars≠glyphs` rows are the crux: `tryComposeFromCharacters`'s own
gate (`clusterEntry.glyphs.length !== chars.length`) exists specifically
to bail out when a character doesn't map 1:1 to a glyph — and for
Devanagari, a virama between two consonants **almost never produces its
own glyph** (0 of 1600 pairs did, in this font) — it either triggers a
fused ligature (1 glyph) or a half-form substitution (2 glyphs, but for 3
characters). Malayalam never hit this because its own conjunct-formation
marks (്യ/്വ/്ല/്ര) are trailing, generic, and reduce a *following*
consonant to a fixed tail — Devanagari's half-form mechanism instead
substitutes the *first* consonant's own shape, and reph reorders the
*first* consonant's glyph to the very end of the whole syllable. Neither
is a "trailing mark," so neither fits `marks{}`'s model without a real
runtime extension.

**What this pass fixed vs. what it's flagging, not fixing:**

- **Rakaar — fixed**, using existing precedent exactly (no new runtime
  code). Shaping "्र" alone against a dotted-circle placeholder (the same
  technique `_build_marks()` already uses for every matra) produces a
  single, dedicated, reusable glyph (`uni094D0930.rakar`) — structurally
  identical to Malayalam's own `virama + "ര"` quirk. `tools/build_glyph_data.py`
  now has a `lang.code == "hi"`-gated block (mirroring the `ml`-gated one
  immediately above it) that records `्र` once and adds it to
  `_composable_marks()`, so all 39 rakaar pairs compose generically via
  the existing `tryComposeStroke` — verified in the coverage numbers below
  (rakaar pairs are *not* in the direct-atom list; only the one `्र` ghost
  is).
- **Nukta's encoding duality — fixed**, reusing `legacyEncodings`/
  `normalizeChillus` (already fully generic — see "Corrections" #2 above).
  `build_glyph_data.py` now writes a `hi`-gated `legacyEncodings` table
  mapping each of the 7 decomposed `base+़` sequences to its precomposed
  atomic codepoint, exactly mirroring Malayalam's own chillu-spelling
  normalization.
- **Half-forms and reph — flagged, not fixed at the time of this pass.**
  These needed a genuinely new runtime composition primitive (not a
  data-table extension) — this pass did *not* implement one in
  `js/src/index.js`, on purpose: that's core runtime logic with real
  correctness/testing stakes, the same category of decision this
  pipeline's shirorekha investigation (see `shirorekha-report.md`) was
  explicitly told to *propose, not implement*. A concrete, generalized
  primitive proposal followed below.
  **Update: since built** — see "Group D/E" further down, and
  `docs/languages/hi/composition-primitives-report.md` for the
  feasibility verification that preceded the implementation. Kept as
  originally written below for the historical record of the finding.

### Proposed fifth/sixth composition primitives (recommendation at the time — since built, see "Group D/E" below)

`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 3 section names two
primitives found during Hindi's profiling ("Synthetic strokes",
"Self-composition") and this pass's shirorekha investigation proposes a
third ("Word-level synthetic strokes" — see `shirorekha-report.md`). This
pass's conjunct-composition finding above proposes two more, for a human
to actually add if approved:

- **Contextual base-form atoms.** A base character can have more than one
  *recorded* form — its ordinary standalone shape, plus one or more
  distinct "contextual form" shapes triggered by what follows it in a
  cluster (Devanagari's half-form is the concrete case: 32–39 consonants
  each have one stable, reusable, non-final-position glyph, verified
  identical regardless of the specific following consonant). Composing a
  cluster built from a contextual-form atom requires generalizing
  `tryComposeFromCharacters`'s character↔glyph alignment from strict 1:1
  to "N characters that this font's own shaping consistently maps to one
  glyph, when preceded/followed by the right trigger" — the trigger
  character(s) (here, a following virama) still consume a position in the
  string but contribute no glyph of their own, and the *recorded* stroke
  used for that position is the contextual-form atom's own recording, not
  the base's ordinary one.
- **Reordering marks.** A mark can be typed in one position but rendered
  in a different one entirely (reph: typed as the cluster's first
  consonant, rendered as a small hook at the very end of the whole
  syllable, contributing no glyph at its own string position at all).
  This needs a distinct primitive from both the existing prefix-mark case
  (typed after its base, rendered before it — still adjacent) and the
  proposed contextual-base-form primitive above (base keeps its own
  string position, just changes shape) — reordering marks change *both*
  their glyph's shape *and* its position relative to the rest of the
  cluster.

Both are generalizable beyond Hindi (any Brahmic script with a half-form-
style non-final consonant mechanism, or a reph-style reordering rule, not
just Devanagari) — worth folding into `docs/LANGUAGE_ONBOARDING_AGENTS.md`
as named primitives once a human decides whether/how to implement them,
per that doc's own "don't generalize before it's actually found" pattern.

### How this was checked

Reproducible directly against the committed `glyph-data.hi.json`:

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
        # n_glyphs == 1 otherwise -> true fusion; n_glyphs == 2 -> half-form
```

## Reduced atom set

Every number below is what `docs/languages/hi/reduced-atom-list.txt`
(committed alongside this doc, grouped/commented) actually contains — not
a summary written independently of it. The flat, comment-free version
(`reduced-atom-list.flat.txt`) is the literal `--simulate-atoms` input used
for the coverage audit further down.

### Group A — standalone atoms (89 total, highest priority)

Trace these first: every other composition (791 clusters, from
consonant+matra to anusvara/visarga combinations) depends on these
existing before it can even be spot-checked, exactly as
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s priority-ordering guidance says.

| Subgroup | Count | Contents |
|---|---|---|
| Independent vowels (incl. 2 loan) | 13 | अ आ इ ई उ ऊ ऋ ए ऐ ओ औ ऍ ऑ |
| Rare (Sanskrit-loanword) vowels | 3 | ऌ ॠ ॡ |
| Consonants (incl. 7 nukta) | 40 | क–ह (33) + क़ ख़ ग़ ज़ ड़ ढ़ फ़ (7) |
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
  has no Unicode decomposition (`unicodedata.decomposition("॥")` is
  empty) — it's its own atomic codepoint, not a 2-character "।।"
  sequence, so `tryComposeFromCharacters`'s `[...cluster]` character-split
  never produces two dandas to reuse. Self-composing it would need the
  same kind of new primitive as double-danda's own doc entry in
  `docs/LANGUAGE_ONBOARDING_AGENTS.md` describes in the abstract, but
  isn't implemented (see `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s
  "Self-composition" — that description is the *target*, this is the gap
  between it and what `tryComposeFromCharacters` actually does today).
  Pragmatically cheap to just record directly (it's one simple shape) —
  included here as its own atom rather than blocking on a primitive for
  a single character. Correction routed back to `profile.md` for the
  record, not applied there by this pass.

### Group D — true ligatures and half-form exceptions, direct recording (43 total)

**Update, post-primitive-build**: the contextual-base-form/reordering
primitives proposed below as a recommendation *have since been built* —
see `docs/languages/hi/composition-primitives-report.md` (feasibility
verification) and `js/src/index.js`'s `tryComposeContextualForm` /
`python/src/jayasree/stroke_compose.py`'s `compose_contextual_form` (the
implementation, mirrored in both engines, gated entirely by
`glyphData.contextualForms` so Malayalam is unaffected). What's left in
Group D is only what *can't* compose even with those primitives:

| Subgroup | Count | Why it's here |
|---|---|---|
| True akhand ligatures | 41 | Genuinely unique fused glyphs — always need direct recording, primitive or not (same as Malayalam's true ligatures). क्क क्त क्ष ङ्क ङ्ख ङ्ग ङ्घ ङ्ङ ङ्य ङ्ह च्च छ्य ज्ञ ट्ट ट्ठ ट्य ठ्ठ ठ्य ड्ड ड्य ढ्य त्त द्द द्ध द्म द्य द्व न्न प्त म्ल ल्ल श्च श्व ष्ट ष्ठ स्न ह्न ह्म ह्य ह्ल ह्व |
| Half-form exceptions | 2 | ड़्य, ढ़्य — verified (`composition-primitives-report.md` §1) to fuse into a genuine ya-phala-style shape distinct from ड़/ढ़'s own ordinary half-form, so they're excluded from the generic half-form atom's derivation and recorded directly instead, same as any true ligature |

The former "Reph pairs" (40) and "Generic half-form pairs" (1480)
subgroups are **gone from Group D entirely** — they now compose
generically at runtime from the two new Group E atoms below, the same way
Malayalam's own subjoined-conjunct marks compose every ്യ/്വ/്ല/്ര pair
without each needing its own recording.

### Group E — contextual-form atoms (40 total, new)

The 32–39 half-form shapes and 1 reph hook Group D used to gate on
building a primitive for — now real, recordable atoms in their own right,
each covering many Group D pairs generically:

| Subgroup | Count | Contents |
|---|---|---|
| Half-form atoms | 39 | One per consonant (except र) — the truncated shape that consonant takes when immediately followed by `्<consonant>`. Ghost sourced from an existing conjunct cluster's own glyph (see `composition-primitives-report.md` §3 for why *not* standalone shaping), keyed by the 2-character trigger (e.g. "क्") |
| Reph hook atom | 1 | The small hook र्+consonant renders as, detached from its own typed position — keyed "र्" |

**Every one of these 40 needs a real human-traced stroke** — they're
genuinely distinct letterforms this font actually renders, verified
identical across every partner consonant (`composition-primitives-report.md`
§1–2), just never individually recorded before. Give the recorder a real
reference ghost the same way rakaar's does — sourced from
`glyphData.contextualForms[trigger].ghost`, not `clusters` (see that
table's own docstring in `tools/build_glyph_data.py` for why: a real
`clusters` entry for e.g. "क्" would make real word-final text ending in
"क्" incorrectly render as the mid-conjunct half-form instead of the
linguistically correct explicit-halant form it already gets today via
virama's own pre-existing mark).

## Coverage audit (pre-recording, simulated)

Per the plan's coverage-audit gate — run against the *exact* runtime
composition code (`tryComposeStroke`/`tryComposeContextualForm`/
`tryComposeFromCharacters`), not a reimplementation:

```
node tools/coverage_report.js --simulate-atoms docs/languages/hi/reduced-atom-list.flat.txt --glyph-data js/src/glyph-data.hi.json
```

```
Coverage report (simulated) - js/src/glyph-data.hi.json
  seeded 174 simulated atoms
  2443 total clusters
  132 direct, 2311 composed, 0 fallback
  coverage: 2443/2443 (100.0%)
```

(Saved verbatim at `docs/languages/hi/coverage-report-pre-recording.txt`.)

**100% — every one of the 2443 clusters `glyph-data.hi.json` defines
resolves to a direct or composed stroke**, now from a **174-atom set**
(down from the original 1652) — the contextual-form primitives closed
exactly the gap "The headline finding" identified, without any
`resolveSegments`/glyph-level change at all (`_conjunct_inputs()`'s
existing brute-forced `clusters` entries already had the real positioning
data every contextual-form composition needed).

174 = 89 (Group A) + 1 (Group B, nukta — included in the atom file purely
so the coverage tool's stub-stroke mechanism can exercise its composition
path; the *real* deliverable is a synthesized stroke, not a traced one) +
1 (Group C) + 43 (Group D) + 40 (Group E).

Post-recording, once real strokes exist, run the identical check against
`js/src/stroke-data.hi.raw.json` (`--stroke-data` instead of
`--simulate-atoms`) — this is the standing gate, not a one-time check.

## What's already committed alongside this doc

- `js/src/glyph-data.hi.json` — generated via `python tools/build_glyph_data.py --lang hindi`, 2443 clusters, 21 marks (`्र` included).
- `js/src/stroke-data.hi.raw.json` / `js/src/stroke-data.hi.json` — both `{}` (empty) for now; Phase 2's recording session starts from here. `tools/validate_data.py` requires all three files to exist together once any `glyph-data*.json` exists, so these are committed as empty stubs rather than left absent.
- `docs/languages/hi/reduced-atom-list.txt` (grouped, commented) and `.flat.txt` (the literal `--simulate-atoms` input).
- `docs/languages/hi/coverage-report-pre-recording.txt`.
- `python/src/jayasree/_chars_hi.py`, registered in `python/src/jayasree/languages.py` as `"hindi"` (code `hi`, carrier consonant क, `default_font` pointing at the vendored Annapurna SIL fixture).
- The shirorekha notice: `profile.md`'s "Shirorekha (headline)" section agreed tracers should skip the top line entirely (it's a synthetic, word-level stroke — see `shirorekha-report.md`), but every ghost outline still *shows* it, since it's part of the font's own glyph. `tools/build_glyph_data.py`'s `_recorder_note()` now writes that instruction into `glyph-data.hi.json`'s `meta.recorderNote` (gated behind `lang.code == "hi"`, absent for Malayalam), and `tools/stroke-recorder.{html,css,js}` render it as a persistent banner whenever a loaded glyph-data file has one — generic, data-driven, no Hindi-specific string in the recorder tool itself. Also baked into the regenerated `tools/stroke-recorder-standalone.hi.html`.
- Two more recorder-UI strings that were previously Malayalam-hardcoded are now per-language data, not tool code: `LanguageSpec.native_name` (this project's own name, "Jayasree," spelled in each script — "जयश्री" for Hindi, "ജയശ്രീ" for Malayalam) drives the page title/`<h1>` via `meta.projectNameNative`, and `LanguageSpec.example_custom_cluster` (a valid example cluster in that script, "क्त" for Hindi — Malayalam's own "ന്ന" isn't valid Devanagari) drives the "Add custom cluster" placeholder via `meta.exampleCustomCluster`. Both are written unconditionally for every registered language (unlike the shirorekha note above), and `js/src/glyph-data.json` (Malayalam) was regenerated too so the mechanism has no special-cased fallback. The "Add custom cluster" row also got a static, script-independent explanation of what a custom cluster actually is (no ghost outline; for spot-checking a cluster outside the reduced set).

## Using the stroke recorder

`tools/stroke-recorder.html` works against `glyph-data.hi.json` with no
Hindi-specific logic hardcoded into it (confirmed by reading
`tools/stroke-recorder.js`: its "reduced set" filter and the shirorekha
banner above are both derived purely from whatever `marks{}`/
`meta.recorderNote` the loaded glyph-data itself defines). Drop
`js/src/glyph-data.hi.json` onto
it (or use its file picker) to start tracing.

`tools/build_standalone_recorder.py` didn't support a second language
before this pass — it hardcoded Malayalam's paths. Extended with a
`--lang` flag (defaulting to `malayalam`, matching every other
`--lang`-aware tool per `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Phase 0):

```
python tools/build_standalone_recorder.py --lang hindi
# → tools/stroke-recorder-standalone.hi.html
```

Verified working: produces a 3.5 MB single-file offline recorder bundling
`glyph-data.hi.json` and the (currently empty) `stroke-data.hi.raw.json`,
landing on the first not-yet-recorded atom automatically. Malayalam's own
`stroke-recorder-standalone.html` is unaffected (byte-for-byte — this
pass explicitly checked and reverted an incidental regeneration of it
that would otherwise have picked up unrelated, pre-existing staleness
between Malayalam's committed standalone file and its own
`stroke-data.raw.json`, out of scope for this pass).

## Review gate

Per the plan's Agent 3 review gate: this worklist and a spot-check sample
of `glyph-data.hi.json`'s ghost outlines (loadable via
`tools/stroke-recorder.html`) need a human who reads/writes Devanagari to
confirm the ghosts look right before Group A recording starts. The
composition-primitive question above ("The headline finding") is a
separate, architectural decision that should be resolved (or at least
explicitly deferred) before Group D recording specifically, since which
subset of Group D actually needs recording depends on it.
