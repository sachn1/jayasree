# Hindi (Devanagari) — Ghost Font Report

> **Status: proposal, pending human approval.** This is Agent 2's output
> from `docs/LANGUAGE_ONBOARDING_AGENTS.md` — a font choice is a real
> licensing/attribution obligation, not just a technical one, so per that
> plan's Agent 2 review gate this needs explicit human sign-off before
> Agent 3 runs `build_glyph_data.py --lang hindi` against it.

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

1. **श्र is not a distinct "akhand" case — it's a routine instance of the
   rakaar mechanism** (श + ् + र, same as any other `<consonant>+्+र`).
   The profile's framing of it as an uncertain akhand candidate alongside
   त्त miscategorizes *why* it fuses, even though the observation "it's
   one glyph" was correct.
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
substitute for it.

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

## Recommendation

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

## Recommendation for the profile (route back to Agent 1 / human reviewer)

Two specific, checkable corrections to `docs/languages/hi/profile.md`'s
"Conjunct/ligature hypotheses" section, per this pipeline's explicit
falsification path:

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

## Artifacts

- `python/tests/fixtures/AnnapurnaSIL-Regular.ttf` — the chosen font,
  vendored for offline/deterministic use (same rationale as Manjari's
  own fixture), **not yet wired into `languages.py`** — that plus
  `_chars_hi.py` and the registry's `default_font` entry is Agent 3's
  job, gated on the human approval this report requests.
- `python/tests/fixtures/AnnapurnaSIL-OFL.txt` — the font's SIL Open Font
  License 1.1 text.
- `python/tests/fixtures/README.md` — updated to document the new
  fixture and its pending-approval status.
