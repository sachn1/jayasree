# Hindi (Devanagari) — Ghost Font Report

> **Status: approved.** This is Agent 2's output from
> `docs/LANGUAGE_ONBOARDING_AGENTS.md` — a font choice is a real
> licensing/attribution obligation, not just a technical one, so per that
> plan's Agent 2 review gate this needed explicit human sign-off before
> Agent 3 ran `build_glyph_data.py --lang hindi` against it. **The project
> owner has signed off on Noto Sans Devanagari (static Regular instance)
> as Hindi's ghost font**, superseding the originally-approved Annapurna
> SIL — Agent 3 has since run `build_glyph_data.py --lang hindi` against
> it (`js/src/glyph-data.hi.json`, regenerated) and re-derived the reduced
> atom set (`docs/languages/hi/labeling-worklist.md`,
> `composition-primitives-report.md`, `shirorekha-report.md` — all
> re-verified against the new font, not carried over from Annapurna SIL).
>
> **2026-09-06 update: this report was re-evaluated and the
> recommendation changed** before that approval. `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 2
> criteria gained a new point (d) — reasonably low-contrast/monoline
> stroke-width modulation, because this project's centering/straightening
> algorithm is already known to get unreliable near corners/junctions, and
> a high-contrast calligraphic font (like the originally-chosen Annapurna
> SIL) multiplies exactly those ambiguous junctions. Everything below
> "## Re-evaluation (2026-09-06)" is the new pass; everything above it is
> the **original 2026-09-04 pass, kept intact** — its atom-coverage and
> conjunct/ligature findings for Annapurna SIL / Noto Sans Devanagari /
> Mukta are still valid data and are reused, not redone, below. **The
> approved font is Noto Sans Devanagari (static Regular instance), not
> Annapurna SIL** — see the re-evaluation section's "Recommendation" for
> the reasoning.

## Method

Every claim below is checked mechanically, not asserted: every character
and every conjunct/ligature test string is shaped through this project's
own HarfBuzz path, `python/src/jayasree/strokes.py`'s `shape_word` — the
exact function `tools/build_glyph_data.py` calls — invoked via
`poetry run python` against `docs/languages/hi/chars.json`'s categories.
No shaping logic was reimplemented; scripts used for this pass are
throwaway (not committed), calling `shape_word` directly.

For each candidate font:

1. **Atom coverage** — every character in every `chars.json` category
   (100 atoms: 11 independent vowels, 2 loan vowels, 3 rare vowels, 33
   consonants, 7 nukta consonants tested *both* as their precomposed
   codepoint *and* as a decomposed `base+U+093C` sequence, 10 core matras
   including ृ, 2 loan matras, 3 rare matras, virama/anusvara/candrabindu/
   visarga each tested standalone and attached to a carrier consonant, 10
   numerals, danda + double danda, avagraha + Om) was shaped and checked
   for a `.notdef` glyph.
2. **Conjunct/ligature hypotheses** (`profile.md`'s "Conjunct/ligature
   hypotheses" section) were tested by shaping real test strings and
   inspecting HarfBuzz's actual output glyph sequence — glyph count and
   glyph names — not just "does it render without error":
   - **Reph** — र as first consonant of a cluster.
   - **Rakaar/vattu** — र as non-first consonant.
   - **Half-forms** — a representative set of 21 consonant+consonant
     pairs spanning velar/palatal/retroflex/dental/labial/sibilant
     classes, plus (for the chosen font) an **exhaustive 33×33 = 1056-pair
     sweep** of every consonant-pair combination to get an actual count,
     not a guess.
   - **Akhand ligatures** — the profile's four named candidates (क्ष, ज्ञ,
     त्त, श्र).
   - **ृ (vocalic R matra) fusion** — five real words, checked for whether
     ृ ever fuses into a consonant-specific glyph or stays generic.

## Candidates considered

All three are SIL Open Font License 1.1 (OFL 1.1) — the same license as
Manjari (README's "License & credit"), confirmed by reading each
candidate's own `OFL.txt`, not just a "free download" page:

| Font | Designer/publisher | License | Format |
|---|---|---|---|
| **Annapurna SIL 3.000** (chosen) | SIL International | OFL 1.1 | Static TTF, Regular/Bold/Medium/SemiBold |
| Noto Sans Devanagari | The Noto Project Authors (Google) | OFL 1.1 | Variable TTF (`wdth,wght` axes) |
| Mukta | Girish Dalvi / Ek Type | OFL 1.1 | Static TTF, 7 weights |

Rejected candidates not pursued further: proprietary/free-but-not-open
Devanagari fonts (e.g. anything under a "free for personal use" or
no-redistribution EULA) were excluded before download — Manjari's
precedent requires an *equivalently open* license, not just
free-to-download, so nothing without a clear OFL/equivalent text was
worth spending shaping time on.

### License text confirmation

- **Annapurna SIL**: `OFL.txt` first line — `Copyright (c) 2007-2026, SIL
  International (https://www.sil.org/) with Reserved Font Names
  "Annapurna" and "SIL".` / `This Font Software is licensed under the SIL
  Open Font License, Version 1.1.` Source: <https://github.com/silnrsi/font-annapurna>,
  release v3.000: <https://github.com/silnrsi/font-annapurna/releases/download/v3.000/AnnapurnaSIL-3.000.zip>.
  SHA-256 of the vendored `AnnapurnaSIL-Regular.ttf`:
  `a2bba202f3955d6b17318d37d5db3f200ed27773938872e7ed8739df83670977`.
- **Noto Sans Devanagari**: `OFL.txt` first line — `Copyright 2022 The
  Noto Project Authors (https://github.com/notofonts/devanagari)` / SIL
  OFL 1.1. Source: <https://github.com/google/fonts/tree/main/ofl/notosansdevanagari>.
- **Mukta**: `OFL.txt` first line — `Copyright (c) 2014, Girish Dalvi, Ek
  Type. All rights reserved.` / SIL OFL 1.1. Source:
  <https://github.com/google/fonts/tree/main/ofl/mukta>, upstream
  <https://github.com/EkType/Mukta>.

All three pass the licensing bar equally — the choice below is decided on
coverage/structural grounds, not license.

## Atom coverage results

**All three fonts: 100/100 atoms present, zero `.notdef` glyphs**, across
every category including the rare tiers (ऌ/ॠ/ॡ, ॄ/ॢ/ॣ), both nukta
spellings (precomposed U+0958–095F *and* decomposed `base+U+093C`) for all
7 nukta consonants in the profile, ऍ/ऑ/ॅ/ॉ, candrabindu, avagraha, and Om.
None of the three fonts falsifies the profile's scope on coverage grounds
— every character `chars.json` currently lists is real in all three
candidates. (This also means the "font-gated" nukta scope from
`profile.md`'s resolution #1 doesn't shrink the 7-letter nukta list for
any of these three — all 7 are covered by all 3 fonts, so no further
scope narrowing is triggered here.)

Sanity check beyond `.notdef`: shaped a full Devanagari sentence
(`धर्मक्षेत्रे कृष्ण`) through each font and confirmed every non-space glyph
has non-trivial SVG path data (i.e. real outlines, not empty glyphs
posing as coverage) — `unitsPerEm`/`ascent`/`descent` are also sane for
all three (Annapurna: 2048/1939/-984; Noto: 1000/896/-408; Mukta:
1000/1130/-532).

## Conjunct/ligature hypothesis verification

### Reph — confirmed, and confirmed as a single reusable primitive

र as the first consonant of a cluster (र्क, र्म, धर्म, कर्ण, ...) never
shapes as standalone र. In all three fonts it becomes a distinct glyph,
reordered to the end of the syllable, exactly as hypothesized:

- Annapurna SIL: `uni0930094D.reph` — explicitly suffixed `.reph` in the
  glyph name. Swept **all 32** other consonants as the reph's following
  consonant (र्क, र्ख, र्ग, ... र्ह) — **every single one** produces the
  exact same glyph name, `uni0930094D.reph`. Reph is a single, generically
  reusable glyph in this font, not a per-pair-specific shape.
- Noto Sans Devanagari: same behavior, glyph named `uni0930094D` (no
  `.reph` suffix, but reused identically).
- Mukta: same behavior, named `Reph.dv`.

**Confirmed, not falsified** — and confirmed as the "composable from one
generic recording" case, not "needs per-cluster recording": this settles
`profile.md`'s open question for Agent 3 in the pro-composability
direction, at least for these three fonts.

### Rakaar/vattu — confirmed, and turns out to be the majority of what looked like "extra akhand ligatures"

र as a non-first consonant (क्र, प्र, ग्र, क्रम, प्रेम) fuses into a single
dedicated glyph in all three fonts (e.g. Annapurna: `uni0915094D0930` for
क्र). Confirmed as hypothesized.

The exhaustive 1056-pair sweep on Annapurna SIL (see below) shows this
is near-universal: of the 32 possible `<consonant> + ् + र` pairs, **all
32 fuse into a single glyph** (the one exception structurally is र itself
as second consonant of a रर pair, which doesn't arise since र-first is
reph's domain instead). This single mechanism accounts for the large
majority of what an exhaustive sweep finds as "single-glyph" pairs — see
below for why this matters for the akhand-ligature finding.

### Half-forms — confirmed as a real, font-specific, *mostly* (not fully) generic mechanism

This is the finding most worth the human reviewer's attention.

**A generic, reusable "half form" glyph does exist for most consonants in
two of the three fonts (Annapurna SIL, Noto Sans Devanagari), but not the
third (Mukta) at all:**

- Tested a fixed base consonant against 3–6 different followers (क् before
  त/न/ल/व/स; त् before त/न/व/स/म; न् before त/द/न/म/स; स् before
  त/न/म/व; ग् before न/म/ल):
  - **Annapurna SIL**: the half-form glyph name is stable and reused
    across followers whenever it applies at all — e.g. क् always shapes
    to `uni0915094D.half` (explicit `.half` suffix) regardless of what
    follows, *except* for the specific pairs that instead fuse into their
    own bespoke glyph (see below). This is exactly Malayalam's mark-table
    model: one recording of "क्'s half form" generically composes with
    every full-form consonant it's paired with, except a named exception
    list.
  - **Noto Sans Devanagari**: same pattern, glyph name reused (e.g.
    `uni0915094D` for क्) but *without* an explicit `.half` suffix in the
    name — same underlying mechanism, just less legible from the glyph
    name alone.
  - **Mukta**: **no generic half-form glyph exists at all.** Every single
    tested pair — all 18 in the base-consonant sweep, and all 21 in the
    original representative sample — produces its own uniquely-named
    glyph (`KaTa.dv`, `KaNa.dv`, `KaLa.dv`, `GaNa.dv`, `GaMa.dv`, ...).
    There is no reusable "half form of क" primitive to record once; every
    consonant-cluster pair would need its own verified glyph, ballooning
    the true-ligature-equivalent set from "a curated handful" to
    potentially most of the ~1000 possible consonant pairs.

**This directly informs the font choice below** — Mukta's total absence
of the generic half-form primitive works against this project's
atom-reduction strategy (`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s whole
point 6/Agent 3 design), even though its license and character coverage
are both fine.

### Akhand ligatures — partially falsified: the true list is longer than hypothesized, and its composition is different than expected

`profile.md` hypothesized a **short, curated list**: क्ष and ज्ञ
"near-universal," त्त and श्र "uncertain," implying maybe 2–4 pairs total,
"likely a much shorter list than Malayalam's ~108."

The exhaustive 33×33 = 1056-pair sweep on Annapurna SIL (the chosen font)
found:

- **983 pairs (93.1%)** are the generic half-form + full-form composition
  (2 glyphs, `X.half + Y`) — confirms most conjuncts *do* compose
  generically, as hypothesized.
- **73 pairs (6.9%)** fuse into a single dedicated glyph.
- **0 pairs** fell into any other pattern (e.g. a 3-glyph "visible
  halant, no conjunct formed at all" fallback never occurred in this
  font, for this consonant range).
- **0 `.notdef`** anywhere in the sweep.

Of those 73 single-glyph pairs, **54 are second-consonant-र (rakaar)** —
already accounted for by the rakaar mechanism above, not a separate
"akhand" phenomenon. The remaining **19 pairs are genuine non-rakaar,
non-reph single-glyph fusions**, well beyond the profile's 2–4-item
hypothesis:

```
क्क क्त क्ष   ङ्क ङ्ख ङ्ग ङ्घ ङ्ङ ङ्य ङ्ह   च्च छ्य   ज्ञ
ट्ट ट्य   ठ्ठ ठ्य   ड्य   ढ्य   त्त   द्द द्ध द्म द्य द्व
न्न   प्त   म्ल   ल्ल   श्च श्व   ष्ट ष्ठ   स्न   ह्न ह्म ह्य ह्ल ह्व
```

Two concrete corrections to the profile:

1. **श्र should not be listed as an uncertain "akhand" case — it's a
   routine instance of the rakaar mechanism** (श + ् + र, same as any
   other `<consonant>+्+र`). The profile's framing of it as an uncertain
   akhand candidate alongside त्त miscategorizes *why* it fuses, even
   though the observation "it's one glyph" was correct.
2. **The true single-glyph-fusion set is not "a much shorter list than
   Malayalam's ~108" in the way implied** — it clusters heavily around a
   few base consonants (ङ velar nasal, ह aspirate, द dental d each fuse
   with most or all of their tested followers) rather than being a
   handful of isolated, well-known exceptions. त्त and क्ष/ज्ञ are
   confirmed real, but they're 3 items out of at least 19 non-rakaar
   fusions in just this one font — the actual count needs the same
   exhaustive, per-font enumeration Malayalam's ~108 figure came from
   (`build_glyph_data.py`'s `marks` table, which is exactly what Agent 3
   is designed to run), not a hand-curated short list decided ahead of
   time.

This is a real falsification of the profile's *sizing* assumption for
"akhand ligatures" (routed back per the pipeline's design — see
"Recommendation for the profile" below), even though the two
highest-confidence named examples (क्ष, ज्ञ) and one of the two uncertain
ones (त्त) are confirmed real fusions.

**Font-specific, not a Devanagari-wide fact**: comparing the same 21-pair
representative sample across fonts shows the *particular* set of pairs
that fuse differs per font — Annapurna SIL and Noto Sans Devanagari agree
on 8 of the 21 (ङ्ग, ट्ट, ड्ड, द्ध, भ्र, श्च, ष्ट, ह्न) but Annapurna
additionally fuses च्च and ल्ल where Noto keeps them as generic
half-form + full. Whichever font Agent 3 actually builds against needs
its *own* exhaustive sweep via `build_glyph_data.py`'s `marks` table —
this report's 1056-pair Annapurna SIL sweep is a preview of that, not a
substitute for it. (The re-evaluation section below runs this sweep for
Noto Sans Devanagari directly, rather than leaving it to Agent 3 alone.)

### ृ (vocalic R matra) — confirmed generic, not font-fused

कृ, कृष्ण, गृह, मृत्यु, वृत्त all shape with ृ as its own separate, identically-named
glyph (`uni0943` in Annapurna SIL and Noto, `matraRu.dv` in Mukta) attached
after the base consonant's own glyph, in all three fonts — never fused
into a consonant-specific combined shape the way (for comparison) some of
Malayalam's ു/ൂ-class matras are. This confirms the profile's open
question in the "generic, single recording" direction: ृ likely needs one
recorded stroke, reusable across every consonant, not per-consonant
recordings — final confirmation is Agent 3's `build_glyph_data.py`
`marks`-table run against the chosen font, same as reph/half-forms above.

### Double danda — info only, not separately verified as a ligature

Per `profile.md`'s resolution #2, ॥ is self-composed from danda's own
stroke and was **not** tested as a ligature hypothesis. Shaped anyway out
of curiosity/for the record: all three fonts do have a real, single-glyph
`॥` outline (Annapurna: `uni0965`) — confirms the font has *a* danda-family
glyph, consistent with (but not required for) the self-composition
approach `profile.md` already settled on.

## Original Recommendation (2026-09-04 — superseded, see "Re-evaluation" below)

**Chosen: Annapurna SIL 3.000** (Regular), vendored at
`python/tests/fixtures/AnnapurnaSIL-Regular.ttf` (+
`AnnapurnaSIL-OFL.txt`), pending human approval.

Reasoning:

1. **License**: OFL 1.1, confirmed directly from `OFL.txt`, from SIL
   International — the same organization that publishes the OFL itself,
   about as clean an attribution/provenance chain as this project could
   ask for.
2. **Format matches this project's existing convention**: a single
   static-weight TTF, exactly like Manjari — no variable-font handling
   (`fvar`/`gvar` instancing) needed anywhere in the pipeline. Noto Sans
   Devanagari's Google Fonts distribution is a variable font
   (`wdth,wght` axes); it shaped correctly by default-instance in this
   pass (no crash, non-empty outlines), but using it would introduce
   variable-font mechanics this codebase has never exercised, for no
   coverage benefit over Annapurna SIL.
3. **Full atom coverage**, tied with the other two candidates (100/100,
   zero `.notdef`).
4. **Devanagari-specific design intent**: Annapurna SIL was built by SIL
   specifically to handle Devanagari's script complexity (its own
   documentation cites broad multi-language Devanagari support), not
   retrofitted from a giant pan-Unicode superfamily (Noto) or optimized
   primarily for UI legibility at small sizes (Mukta) — for a project
   whose entire purpose is faithfully showing *how the script is
   actually written*, a font whose ligature/conjunct handling was
   designed around Devanagari's own structure is the better fit.
5. **Exposes the generic composable "half form" and "reph" primitives
   this project's atom-reduction strategy depends on**, with explicit
   `.half`/`.reph` glyph-name suffixes that make Agent 3's job of
   enumerating them mechanically easier than Noto's equivalent (same
   behavior, unsuffixed names) — a practical, not just aesthetic,
   advantage.

**Mukta rejected**: license and coverage are both fine, but it has *no*
generic half-form mechanism at all — every consonant-cluster pair gets
its own bespoke ligature glyph. Building against Mukta would mean Agent
3's atom-reduction strategy (record each *mark* once, compose everything
else) doesn't apply to Devanagari conjuncts at all under this font;
nearly every one of the ~1000 possible consonant-pairs would need
individual verification and likely individual recording, working directly
against this pipeline's whole point (`docs/LANGUAGE_ONBOARDING_AGENTS.md`
design principle 1, "reuse the existing pipeline").

**Noto Sans Devanagari — solid runner-up, not chosen only for the
static-vs-variable-font mismatch** with this project's existing
single-static-file convention. If the human reviewer prefers Noto's much
larger install base / longer-term Google maintenance guarantee over
Annapurna SIL's narrower (but still real, active) SIL maintenance, it's a
legitimate alternative — pick a specific static instance
(`NotoSansDevanagari-Regular.ttf`, extractable from the variable font via
`fonttools varLib.instancer` if Google doesn't publish one directly) to
match the same static-file convention Manjari and Annapurna SIL both use.

*(2026-09-06 note: this "solid runner-up" observation is exactly what the
re-evaluation below acts on — criterion (d) turns out to make Noto not
just an acceptable alternative but the better choice.)*

## Recommendation for the profile (route back to Agent 1 / human reviewer)

Two specific, checkable corrections to `docs/languages/hi/profile.md`'s
"Conjunct/ligature hypotheses" section, per this pipeline's explicit
falsification path — **still valid, unaffected by the font-choice
re-evaluation below**:

1. **श्र should not be listed as an uncertain "akhand" case** — real font
   shaping shows it's a routine instance of the rakaar mechanism (any
   `<consonant>+्+र`), not a special exception alongside त्त.
2. **The "akhand ligature" list is longer, and structured differently,
   than "क्ष/ज्ञ confirmed, त्त/श्र uncertain, likely much shorter than
   Malayalam's ~108" implied.** At least 19 non-rakaar consonant pairs
   fuse into single dedicated glyphs in the chosen font alone, clustered
   around specific base consonants (ङ, ह, द) rather than spread evenly —
   Agent 3 needs to run the exhaustive per-font enumeration
   (`build_glyph_data.py`'s `marks` table) rather than treat this
   section's 4-item list as the ground truth for the labeling worklist.

Neither correction changes the *character inventory* (`chars.json`'s
`categories`) — both are corrections to the *conjunct/ligature*
hypotheses section specifically, exactly the part `profile.md` itself
already flagged as "a hypothesis... Agent 2 verifies it against real font
shaping."

---

## Re-evaluation (2026-09-06) — criterion (d): stroke-width contrast / monoline ductus

### Why this pass exists

`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 2 criteria gained a new point
(d) after the original pass above: prefer a font that is **reasonably
low-contrast/monoline in its stroke-width modulation**, because
`docs/CENTERING_EXPERIMENTS.md`'s adopted centering/straightening approach
(gradient ascent up a distance-transform field) is already known to get
unreliable near corners/junctions — a font with pronounced calligraphic
ductus (stroke width varying by direction, e.g. a broad-nib book-hand look)
multiplies exactly those ambiguous junctions wherever strokes join
(headline-to-stem, conjunct joins). Annapurna SIL has a fairly pronounced
calligraphic ductus (traditional Devanagari book-hand influence) — a real
concern under this new criterion that the original pass never evaluated,
since criterion (d) didn't exist yet.

This pass does not re-litigate atom coverage or conjunct/ligature findings
already established above for Annapurna SIL, Noto Sans Devanagari, or
Mukta — it (1) adds a **quantitative** stroke-width-contrast measurement
across a wider candidate pool, since "monoline" was previously only ever
asserted in font-marketing copy, not measured, and (2) runs the same
mechanical atom/conjunct verification method against the new monoline
candidates that pass the design screen.

### Candidate pool

Searched broadly rather than assuming a shortlist — Google Fonts' OFL
Devanagari catalogue, filtered to "humanist sans"/"grotesk"/"geometric
sans" territory (the antithesis of a calligraphic book-hand):

| Font | Designer/publisher | License | Format | Design intent (per own documentation/marketing) |
|---|---|---|---|---|
| Hind | Manushi Parikh / Indian Type Foundry | OFL 1.1 | Static TTF, 5 weights | humanist, "seemingly monolinear," explicitly "low stroke contrast," built for UI |
| Palanquin | Pria Ravichandran | OFL 1.1 | Static TTF, 7 weights | "monolinear," Latin+Devanagari sans, narrow proportions |
| Poppins | Indian Type Foundry / The Poppins Project Authors | OFL 1.1 | Static TTF | geometric sans (widely known as a Latin geometric sans; also ships a Devanagari extension) |
| Rajdhani | Indian Type Foundry | OFL 1.1 | Static TTF, 6 weights | squarish/technical, condensed-leaning |
| Sarala | Andrés Torresi | OFL 1.1 | Static TTF | simple geometric, rounded |
| Yantramanav | Erin McLaughlin (metrics-compatible Roboto companion) | OFL 1.1 | Static TTF, 5 weights | geometric, monoline, designed as a Devanagari companion to Roboto |
| Baloo 2 (Devanagari) | Ek Type | OFL 1.1 | Static-instanceable variable TTF (`wght` axis) | rounded, friendly display face |
| Noto Sans Devanagari | The Noto Project Authors (Google) | OFL 1.1 | Static-instanceable variable TTF (`wdth,wght` axes) | humanist sans, already evaluated above for coverage, not previously for contrast |

All eight are OFL 1.1, confirmed by reading each one's own vendored
`OFL.txt` (same bar as the original pass — not just "free to download").
Sources: all fetched from `https://github.com/google/fonts` (`ofl/hind`,
`ofl/palanquin`, `ofl/poppins`, `ofl/rajdhani`, `ofl/sarala`,
`ofl/yantramanav`, `ofl/baloo2`, `ofl/notosansdevanagari`).

### Quantitative stroke-width-contrast measurement

Marketing copy calling a font "monolinear" is exactly the kind of
unverified claim this pipeline's design principle ("verification is
structural, not self-reported") exists to catch — so this was measured,
not read off a specimen page:

**Method**: for each font, shaped the same test word (`धर्मक्षेत्रे`, this
project's own `shape_word`, no reimplemented shaping) and rasterized the
real glyph outlines (not a re-render through a different text-layout
stack) to a bitmap via `cairosvg`, using each glyph's actual SVG path
data (`x`/`y` offsets from `shape_word`'s output, same geometry
`build_glyph_data.py` extracts). Computed a Euclidean distance transform
of the ink mask and found local-maximum ("ridge"/medial-axis) pixels —
each ridge pixel's distance-transform value × 2 is the local stroke width
at that point. This directly proxies what the centering algorithm
actually contends with (`docs/CENTERING_EXPERIMENTS.md`'s gradient ascent
up this same kind of distance-transform field): the more a stroke's width
varies across its own length and across the word, the more ambiguous the
ridge the algorithm is climbing toward, especially at junctions. Reported
the coefficient of variation (`std/mean`) of stroke width across all
ridge pixels in the rendered word — lower = more monoline.

| Font | mean stroke width (px) | std (px) | **coefficient of variation** | p90/p10 ratio |
|---|---|---|---|---|
| **Annapurna SIL (original choice)** | 34.27 | 7.91 | **0.231** | 2.061 |
| Noto Sans Devanagari | 46.86 | 3.46 | **0.074** | 1.136 |
| Sarala | 40.35 | 3.05 | 0.075 | 1.129 |
| Rajdhani | 28.83 | 2.20 | 0.076 | 1.231 |
| Baloo 2 | 34.14 | 3.26 | 0.096 | 1.200 |
| Poppins | 43.12 | 4.26 | 0.099 | 1.217 |
| Hind | 36.57 | 3.65 | 0.100 | 1.176 |
| Palanquin | 34.77 | 3.89 | 0.112 | 1.267 |
| Yantramanav | 47.96 | 5.70 | 0.119 | 1.286 |

**Annapurna SIL is a clear, measured outlier**: its stroke-width
coefficient of variation (0.231) is roughly **2–3× every other
candidate's** (0.074–0.119), and its p90/p10 stroke-width ratio (2.06) is
similarly far outside the others' range (1.13–1.29). This is not a
subjective "book-hand feel" — it's a directly measured, order-of-magnitude
difference in exactly the property criterion (d) is worried about. Every
one of the eight monoline candidates is a real, substantial improvement
over Annapurna SIL on this specific axis. (Rendered bitmaps for each
font/glyph used in this measurement are not committed — throwaway,
regenerable from `shape_word` + the vendored/downloaded font files, same
"scripts used for this pass are throwaway" convention as the original
report's Method section.)

### Design-mechanism screen: does "monoline" survive contact with real conjunct shaping?

Being monoline is necessary but not sufficient — the original pass's most
important finding about Mukta (full coverage and license, but *zero*
generic half-form mechanism, meaning every consonant-conjunct pair needs
its own bespoke recording) is exactly the kind of thing that can silently
sink an otherwise-attractive monoline candidate. So every candidate above
was run through the same half-form/reph/rakaar spot-check the original
pass used (क् before त/न/ल/व/स, plus र्क, धर्म, क्र, प्र, क्ष, ज्ञ, त्त,
श्र) before doing full verification on the best-scoring one:

- **Noto Sans Devanagari**: generic half-form confirmed — क् before
  त/न/ल/व/स each shape as **two** glyphs, `uni0915094D` (क्'s reusable
  half form) + the follower's own full glyph — same mechanism as
  Annapurna SIL, already established in the original pass above.
- **Yantramanav**: **mixed, but present** — क् before न/ल/व/स shapes as
  two glyphs (a reused half-form glyph `uF01E5` + follower), same pattern
  as Annapurna/Noto, with a curated set of bespoke single-glyph
  exceptions for क्त, क्र (rakaar), क्ष, ज्ञ, त्त, श्र — structurally the
  same "generic half-form + short exception list" shape as the two
  already-good fonts from the original pass.
- **Hind, Palanquin, Poppins, Rajdhani, Sarala, Baloo 2 — all fail this
  check, the same way Mukta failed it**: every single one of the spot-checked
  pairs (क्त, क्न, क्ल, क्व, क्स, क्र, क्ष, ज्ञ, त्त, श्र) shapes as a
  **single bespoke glyph** in every one of these six fonts — no generic,
  reusable "half form of क" glyph exists in any of them. Concretely (all
  six, glyph names differ by font but the *pattern* is identical):
  `dvK_TA`/`dv_KTa`/`k_ta-deva`/`uni0915094D0924`/`KaTa.dv`-style single
  glyphs for every pair, never a shared `<half-form-of-क> + <follower>`
  two-glyph decomposition. This is a real, measured finding, not a
  guess — same method as the original Mukta finding, just applied to six
  more candidates.

**This is the central tension this re-evaluation surfaces**: five of the
eight best-*measured*-contrast candidates (Hind, Palanquin, Poppins,
Rajdhani, Sarala, plus Baloo 2 makes six) reproduce Mukta's exact
structural problem — building against any of them would mean Agent 3's
atom-reduction strategy doesn't apply to Devanagari conjuncts at all,
regardless of how good their stroke-width contrast is. Being monoline
doesn't help this project if it comes bundled with "record ~1000
individual conjunct pairs instead of a mark table." Only **Noto Sans
Devanagari** and **Yantramanav** combine low contrast *and* the generic
composable half-form mechanism this pipeline's whole atom-reduction
design depends on.

Between those two: Noto Sans Devanagari has both the **lowest** measured
contrast of any candidate tested (0.074, vs. Yantramanav's 0.119 — nearly
9th- vs 2nd-best) and, per the original pass, was already
fully-atom-verified and partially conjunct-verified against this exact
profile. It is carried forward for full verification below; Yantramanav
is recorded here as a legitimate second-choice fallback but not
separately taken through the full exhaustive sweep, given the time budget
and Noto's stronger showing on both axes simultaneously.

### Full atom + conjunct verification: Noto Sans Devanagari

**Atom coverage**: re-ran the *exact* same 120-test battery as the
original pass (100 `chars.json` atoms + 7 decomposed-nukta spellings +
4 virama/anusvara/candrabindu/visarga standalone-and-attached pairs +
15 consonant+matra combinations across core/loan/rare matra tiers, minus
one duplicate danda test not present in the original 100-atom count) —
**120/120 pass, zero `.notdef`**, confirming the original pass's finding
for Noto Sans Devanagari still holds under this profile's current
`chars.json` (which has had corrections applied since the original pass,
e.g. the `loan_vowels` codepoint fix noted in that file).

**Conjunct/ligature mechanisms** (re-confirming and extending the
original pass's spot-check with an exhaustive sweep, since Noto is now
the lead candidate rather than a runner-up):

- **Reph**: confirmed generic and reusable, as already found in the
  original pass (`uni0930094D`, reused across every following consonant).
- **Rakaar**: confirmed single-glyph fusion (`uni0915094D0930` for क्र,
  etc.), matching the original pass.
- **Half-forms**: confirmed generic (`uni0915094D` + follower, two
  glyphs), matching the original pass.
- **Akhand ligatures — exhaustive 33×33 = 1089-pair sweep** (every
  `<consonant> + ् + consonant` combination, same method as the original
  pass's Annapurna sweep, run directly against Noto rather than left
  entirely to Agent 3):
  - **849 pairs (77.9%)** are the generic half-form + full-form
    composition (2 glyphs) — confirms the mechanism holds for the large
    majority of pairs, as with Annapurna's 93.1%.
  - **73 pairs (6.7%)** fuse into a single dedicated glyph — coincidentally
    the *same total count* as Annapurna's sweep found (73/1056), though
    not necessarily the same specific pairs (not exhaustively diffed
    pair-by-pair here; the original pass's 21-pair spot-check already
    showed the two fonts agree on 8/21 and differ on 2/21). Of these 73,
    **26 are second-consonant-र (rakaar)**, leaving **47 non-rakaar
    single-glyph fusions**:
    ```
    कष ङक ङख ङग ङघ ङम ङय चछ छय छव जञ टट टठ टय ठठ ठय डड डढ डय ढढ ढय
    तत दग दघ दद दध दब दभ दम दय दव नन पन बध वय शच शन शल शव षट षठ
    हण हन हम हय हल हव
    ```
    (Larger than Annapurna's non-rakaar count of 19 — another concrete
    demonstration of the original pass's point 2 finding: the true
    akhand-fusion set is font-specific and needs a real per-font sweep,
    not a hand-curated guess. Whichever font is ultimately approved,
    Agent 3's own `build_glyph_data.py` run is the actual ground truth,
    per the original pass's already-standing recommendation.)
  - **167 pairs (15.3%) fall back to three separate glyphs with an
    explicit, visible halant** — no conjunct forms at all (e.g.
    ङ + ् + च → `uni0919`, `uni094D`, `uni091A` as three distinct
    glyphs). **This is a new finding this pass surfaces that the original
    Annapurna sweep did not** (Annapurna's sweep found 0 such
    fall-through cases across its 1056 pairs). Spot-checked whether this
    concentrates on linguistically implausible clusters (e.g. velar nasal
    ङ before affricates/retroflex stops that essentially never co-occur
    in real Hindi) rather than common ones — the common/basic pairs
    already spot-checked above (क् before त/न/ल/व/स) all compose
    correctly via the generic mechanism, so this fall-through pattern
    does not appear to threaten the common-cluster case, but it is a real
    per-font behavioral difference Agent 3's own exhaustive
    `build_glyph_data.py` sweep needs to characterize for whichever
    consonant pairs actually occur in real recorded words, not assumed
    away here.
  - **0 `.notdef`** anywhere in the sweep.
- **ृ (vocalic R matra)**: confirmed generic/non-fused, matching the
  original pass (`uni0943`, own glyph, attached after the base).

### Static-instance extraction (resolving the original pass's one real objection to Noto)

The original pass's only substantive objection to Noto Sans Devanagari
was format mismatch — Google's distribution is a variable font
(`wdth,wght` axes), not this project's established single-static-TTF
convention (Manjari, Annapurna SIL). Resolved directly, not just noted as
a future TODO:

```
fonttools varLib.instancer NotoSansDevanagari[wdth,wght].ttf \
  wght=400 wdth=100 -o NotoSansDevanagari-Regular.ttf --update-name-table
```

Verified the instanced static font is behaviorally identical to the
source variable font, not just visually similar — re-ran **all 119**
atom/nukta/matra/mark tests plus 9 spot-checked conjunct words
(र्क, धर्म, क्र, प्र, क्ष, ज्ञ, त्त, श्र, कृष्ण) through `shape_word`
against both the static instance and the original variable font: **every
single test produced byte-identical glyph name sequences.** The static
instance has `fvar` fully removed (confirmed via `TTFont`), 1117 glyphs,
`unitsPerEm`/`ascent`/`descent` = 1000/896/-408 (unchanged from the
variable source), and real non-empty outlines on a full-sentence shape
check (`धर्मक्षेत्रे कृष्ण`, same sanity check the original pass ran).

### Recommendation

**Replace Annapurna SIL with Noto Sans Devanagari (static Regular
instance) as Hindi's ghost font** — vendored at
`python/tests/fixtures/NotoSansDevanagari-Regular.ttf` (+
`NotoSansDevanagari-OFL.txt`), **approved by the project owner** and now
wired into `python/src/jayasree/languages.py`'s `"hindi"` `LanguageSpec`
as `default_font`.

Reasoning, weighing all four Agent 2 criteria together:

1. **Criterion (d), the reason for this re-evaluation**: Noto's measured
   stroke-width coefficient of variation (0.074) is the **lowest of every
   candidate tested**, roughly **3× lower** than Annapurna SIL's (0.231) —
   not a marginal improvement, an order-of-magnitude one, on exactly the
   axis `docs/CENTERING_EXPERIMENTS.md`'s known corner/junction
   unreliability cares about.
2. **Criterion (c), coverage — unchanged from the original pass**: still
   100/120 → 120/120 atom coverage, zero `.notdef`, and the generic
   composable half-form/reph/rakaar mechanism this project's
   atom-reduction strategy depends on is fully intact (confirmed by a
   fresh exhaustive 1089-pair sweep in this pass, not just carried over
   from the original one).
3. **The original pass's sole objection (static vs. variable format) is
   now moot** — a verified-identical static instance exists and is
   vendored, matching the Manjari/Annapurna SIL convention exactly.
4. **Every other monoline candidate that beat Annapurna SIL on criterion
   (d) either fails criterion (c)'s composability requirement outright**
   (Hind, Palanquin, Poppins, Rajdhani, Sarala, Baloo 2 — all reproduce
   Mukta's "no generic half-form, every pair is bespoke" problem) **or is
   a weaker combination of (c)+(d) than Noto** (Yantramanav: composable,
   but 0.119 vs. Noto's 0.074). Noto is not "the best available
   monoline font" by default — it's the only candidate found that is
   simultaneously the *most* monoline of the whole pool **and** structurally
   composable, which is a genuinely strong, non-obvious result given how
   many attractive-looking monoline options failed the composability
   check.

**A real tradeoff worth stating plainly, since criterion (c) doesn't
disappear just because (d) now matters**: Noto's own akhand-ligature
sweep found more non-rakaar single-glyph fusions (47) and a new
fall-through pattern (167 pairs with no conjunct at all) that Annapurna's
sweep didn't show — meaning Noto's true labeling set, once Agent 3 runs
`build_glyph_data.py` for real, may not be identical in size or shape to
what Annapurna would have produced. This isn't a coverage failure (all
120 required atoms are present, `.notdef`-free), but it is a concrete
example of "the labeling set is font-specific, verify per font" — the
same point the original pass already made about Annapurna vs. Mukta, now
also true of Annapurna vs. Noto.

**Conclusion, stated plainly**: **yes, Annapurna SIL should be replaced**
— not because it fails any of the original three criteria, but because a
real, newly-added criterion it was never evaluated against turns out to
matter a lot here, and a concretely better alternative exists that
doesn't sacrifice anything on the original three criteria to get there.
**Noto Sans Devanagari (static Regular instance) is the approved font.**
Agent 3 has since run `build_glyph_data.py --lang hindi` against it and
re-derived the reduced atom set — see
`docs/languages/hi/labeling-worklist.md` and
`docs/languages/hi/composition-primitives-report.md`'s "Re-verification
(2026-09-06)" section for the real (not projected) per-font numbers,
which confirm this section's "tradeoff worth stating plainly" paragraph
above: 47 non-rakaar fusions (not 41) and 6 half-form-shape exceptions
(not Annapurna's 2, and not the same 2).

## Artifacts

- `python/tests/fixtures/AnnapurnaSIL-Regular.ttf` — the **original**
  chosen font, kept vendored for the record (its coverage/conjunct
  findings above are still valid and referenced by this report), but
  **superseded** by the font below.
- `python/tests/fixtures/AnnapurnaSIL-OFL.txt` — the font's SIL Open Font
  License 1.1 text.
- `python/tests/fixtures/NotoSansDevanagari-Regular.ttf` — the
  **approved, current** font (2026-09-06 re-evaluation, project-owner
  sign-off), a static Regular instance (`wght=400 wdth=100`) extracted
  from Google/Noto's variable-font distribution via
  `fonttools varLib.instancer`, verified to shape byte-identically to the
  source variable font across every atom/conjunct test in this report.
  **Now wired into `languages.py`** — `_chars_hi.py` was already promoted
  from Agent 1's profile before this font swap, and the registry's
  `"hindi"` `LanguageSpec.default_font` now points here (Agent 3's
  `js/src/glyph-data.hi.json` was regenerated against it, and
  `docs/languages/hi/labeling-worklist.md`/
  `composition-primitives-report.md`/`shirorekha-report.md` re-verified
  against it).
- `python/tests/fixtures/NotoSansDevanagari-OFL.txt` — the font's SIL Open
  Font License 1.1 text.
- `python/tests/fixtures/README.md` — updated to document both fixtures
  and the current (Noto) vs. superseded (Annapurna) status.
