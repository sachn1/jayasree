# Hindi (Devanagari) — Composition Primitives: Feasibility Verification

> **Status: verification complete, re-run against Noto Sans Devanagari
> (2026-09-06).** This report originally verified the half-form/reph
> composition primitives against **Annapurna SIL** (kept below as
> "Original pass (Annapurna SIL)" for the historical record, since that
> font's finding informed the primitive's actual implementation in
> `js/src/index.js`/`stroke_compose.py`). After `docs/languages/hi/
> font-report.md`'s re-evaluation replaced Annapurna SIL with **Noto Sans
> Devanagari** (static Regular instance, project-owner-approved), Agent 3
> re-ran this exact verification against the regenerated
> `js/src/glyph-data.hi.json` — this file's own `marks`/`contextualForms`
> tables are the ground truth for whichever font actually produced them,
> per this project's own "verify per font, don't assume" pattern
> (`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 3 section). **The
> primitive itself still holds for Noto** (same conclusion as Annapurna),
> but the *specific* set of half-form-shape exceptions is different — see
> "Re-verification (2026-09-06)" below, which is the actual data behind
> the current `tools/build_glyph_data.py`'s `_HI_HALFFORM_EXCLUDED_PAIRS`
> and `docs/languages/hi/reduced-atom-list.txt`'s Group D2/E1 counts.

## Conclusion (current, Noto Sans Devanagari)

**The premise holds, with a different, larger set of named exceptions
than Annapurna SIL had.** Every consonant's half-form is a single,
reusable shape *for the overwhelming majority of its partners* — but for
5 of 39 consonants, one or two specific partners produce a distinctly
different half-form glyph that must be excluded and recorded directly
instead of composed generically. One consonant (द) has **no** generic
half-form at all under Noto — every one of its conjunct pairs either
fuses into a single glyph or falls back to three fully separate glyphs
(explicit visible halant), both of which already compose without any
half-form atom. The reph hook remains a single, reusable shape with zero
exceptions, exactly as under Annapurna SIL. As with the original pass,
ghosts still cannot be sourced by shaping the trigger sequence standalone
— they must be extracted from an already-shaped conjunct-pair cluster
entry.

## Re-verification (2026-09-06): Noto Sans Devanagari

Re-ran the identical method against the regenerated
`js/src/glyph-data.hi.json` (built from
`python/tests/fixtures/NotoSansDevanagari-Regular.ttf`) and
`python/src/jayasree/_chars_hi.py`'s `CONSONANTS` (40 consonants, including
the 7 nukta ones) — the same groupby-and-compare, no new shaping. Numbers
below are directly reproducible via the snippet in "How this was checked".

### 1. Half-form shape identity (in-context) — different exception set

For every consonant C1 except र (39 total), grouped all C2 partners whose
`clusters[C1+्+C2]` entry has exactly 2 glyphs by `glyphs[0]["d"]`
(identical string ⇒ same shape):

- **33 of 39 consonants**: exactly one shape across every 2-glyph
  partner, no exceptions — same clean picture as Annapurna's 37/39,
  just a different count.
- **5 of 39 consonants** have **two** distinct half-form shapes among
  their 2-glyph partners — a genuinely different (and larger) exception
  set than Annapurna's ड़/ढ़-only finding:
  - **छ** — identical across 37 partners, distinct shape before **र**
    (छ्र).
  - **ज** — identical across 37 partners, distinct shape before **ज**
    itself (ज्ज, a self-conjunct).
  - **न** — identical across 36 partners, distinct shape before **both
    थ and ध** (न्थ, न्ध) — the only consonant with two exception
    partners rather than one.
  - **म** — identical across 38 partners, distinct shape before **भ**
    (म्भ).
  - **ज़** (nukta) — identical across 38 partners, distinct shape before
    **ज** (ज़्ज).

  Total: **6 exception pairs** (छ्र, ज्ज, न्थ, न्ध, म्भ, ज़्ज) — up from
  Annapurna's 2 (ड़्य, ढ़्य). Verified these are still genuine 2-glyph
  pairs (not 1-glyph akhand fusions) — the *shape* differs, not the
  glyph count, so they're a half-form-exception, not a true-ligature,
  though both are handled the same way (direct recording, excluded from
  the generic contextual-form derivation).
- **1 of 39 consonants (द) has zero 2-glyph partners at all.** Every
  द+्+C2 pair is either a single-glyph fusion (9 pairs: दग दघ दद दध दब
  दभ दम दय दव — already true akhand ligatures, direct recording
  regardless) or a 3-glyph fallthrough (the remaining 30 pairs — chars
  == glyphs == 3, already generically composable via the existing
  per-character fallback, no half-form primitive needed). **This is not
  a gap**: द simply never needs a `contextualForms["द्"]` entry under
  this font, and `tools/build_glyph_data.py`'s `_build_contextual_forms`
  correctly produces none for it (confirmed: 38 half-form entries in
  the regenerated `glyph-data.hi.json`'s `contextualForms`, not 39 — the
  missing one is exactly द, not a bug).
- **Annapurna's own exception (ड़्य, ढ़्य) does not reproduce under
  Noto** — checked directly: `clusters["ड़्य"]`/`clusters["ढ़्य"]` are
  **3-glyph fallthroughs** under Noto (chars == glyphs, explicit visible
  halant), not the 1-glyph ya-phala-style fusion Annapurna produced. This
  is exactly the kind of font-specific difference
  `docs/languages/hi/labeling-worklist.md`'s "Corrections" section and
  `font-report.md`'s re-evaluation both already warned to expect —
  `tools/build_glyph_data.py`'s `_HI_HALFFORM_EXCLUDED_PAIRS` was updated
  to Noto's real 6 pairs (replacing Annapurna's 2), not merged with them.

**Verdict: every consonant genuinely has at most one reusable half-form
shape, except 5 with one exception partner each (6 pairs total) and 1
(द) with none at all — a real, font-specific finding, re-derived from
scratch rather than assumed to carry over from Annapurna.**

### 2. Reph hook shape identity (in-context) — unchanged conclusion

`clusters["र"+्+C2].glyphs[1].d"` compared across all 40 reph pairs (33
plain consonants + 7 nukta): **100% identical, one single shape, zero
exceptions** — same clean result as Annapurna SIL.

### 3. Standalone (word-final) shaping vs. in-context shape — unchanged conclusion

Re-checked whether shaping the 2-character trigger alone (`shape_word`,
no following consonant) reproduces the real in-context shape:

- **Half-forms: 0 of 38 consonants' standalone shaping matched** the
  in-context half-form shape (down from Annapurna's 7/37 — under Noto,
  standalone `<consonant>+्` renders the full consonant plus an explicit
  halant mark for every single one of the 38 tested, not just most of
  them). Same underlying reason as the original finding: this is the
  linguistically distinct word-final form, not a shaping bug.
- **Reph: standalone "र्" still doesn't match** — shapes to 2 glyphs
  under Noto too, but structurally different from the in-context reph
  hook (first glyph is a full-shape variant, not the small detached
  hook).

**Verdict: standalone shaping remains unusable as the ghost source for
either primitive, confirmed fresh against Noto — not assumed to transfer
from the Annapurna finding.**

### How this was checked

Reproducible directly against the regenerated `glyph-data.hi.json`:

```python
import json
data = json.load(open("js/src/glyph-data.hi.json", encoding="utf-8"))
clusters = data["clusters"]
consonants = list(__import__("jayasree._chars_hi", fromlist=["CONSONANTS"]).CONSONANTS)
virama = "्"
for c1 in consonants:
    if c1 == "र":
        continue
    shapes = {}
    for c2 in consonants:
        entry = clusters.get(c1 + virama + c2)
        if entry and len(entry["glyphs"]) == 2:
            shapes.setdefault(entry["glyphs"][0]["d"], []).append(c2)
    # len(shapes) > 1 -> this consonant has half-form-shape exceptions
    # len(shapes) == 0 -> this consonant has no generic half-form at all
```

Plus one call to `python/src/jayasree/strokes.py`'s `shape_word` per
consonant for §3 (standalone-vs-in-context), same as the original pass.

## Implication for Agent 3's reduced atom set (Noto)

- **Group D (direct recording) grows from Annapurna's 43 to 53**: 47
  true akhand ligatures (up from 41 — see
  `docs/languages/hi/labeling-worklist.md`'s updated akhand-ligature
  sweep) + 6 half-form-shape exceptions (up from 2: छ्र, ज्ज, न्थ, न्ध,
  म्भ, ज़्ज replace ड़्य, ढ़्य).
- **Group E (contextual-form atoms) shrinks from Annapurna's 40 to 39**:
  38 half-form atoms (down from 39 — द has none) + 1 reph atom
  (unchanged).
- Net reduced-atom-set size: **183** (up from Annapurna's 174) — see
  `docs/languages/hi/labeling-worklist.md` for the full breakdown and
  `docs/languages/hi/coverage-report-pre-recording.txt` for the
  100%-coverage confirmation against this new set.

## Original pass (Annapurna SIL, 2026-09-05) — kept for the historical record

This checks the premise behind `docs/languages/hi/labeling-worklist.md`'s
"headline finding" — that Devanagari's half-forms and reph can each
collapse to a small number of reusable recorded atoms, composed
generically at runtime — against real shaped data from
`AnnapurnaSIL-Regular.ttf`, before any runtime composition code was
written. **Superseded by the re-verification above** (Annapurna SIL is no
longer the project's chosen font — see `font-report.md`'s re-evaluation),
kept intact here because it's what originally justified building
`tryComposeContextualForm`/`compose_contextual_form` in the first place.

### 1. Half-form shape identity (in-context) [Annapurna SIL]

For every consonant C1 (except र, which is never a generic half-form —
it's always reph) and every consonant C2 it pairs with as a generic
half-form pair (chars=3, glyphs=2, per the labeling worklist's own
category sweep), compared `clusters[C1+virama+C2].glyphs[0].d` across all
C2 partners:

- **37 of 39 consonants**: exactly one shape, identical across every
  partner, no exceptions.
- **2 of 39 consonants** (ड़, ढ़ — both nukta retroflex flaps): identical
  across 38 of 39 partners, with exactly one partner (्+य specifically,
  i.e. ड़्य and ढ़्य) producing a distinctly different, longer glyph path —
  consistent with Devanagari's well-known consonant+ya fusion behavior
  (a "ya-phala" style special case, structurally the same category of
  thing as any true akhand ligature). **Recommendation**: treat ड़्य and
  ढ़्य as two more true-ligature-style direct recordings (moving them out
  of the generic-half-form bucket, alongside the 41 already-known true
  ligatures) rather than letting them invalidate ड़/ढ़'s half-form atom for
  their other 38 partners. Negligible effect on the total count (+2).

**Verdict: every consonant genuinely has one reusable half-form shape.**

### 2. Reph hook shape identity (in-context) [Annapurna SIL]

`clusters["र"+virama+C2].glyphs[1].d` compared across all 40 reph pairs:
**100% identical, one single shape, zero exceptions.**

### 3. Standalone (word-final) shaping vs. in-context shape [Annapurna SIL]

Checked whether shaping the 2-character trigger alone (`shape_word`, same
technique `_build_marks()` uses for rakaar/matras — HarfBuzz shapes it as
if at word end, no following consonant) reproduces the real in-context
shape from §1/§2:

- **Half-forms: only 7 of 37 consonants' standalone shaping happened to
  match.** For the other 30, standalone `<consonant>+virama` renders as a
  visibly different construct — this font shows the **full consonant
  shape plus a separate, explicit halant stroke** at word end (the
  linguistically correct rendering for an actual word-final virama, e.g.
  the "न्" ending "भगवान्"), which is a genuinely different glyph from the
  **truncated half-form** used mid-conjunct. These are two real, distinct
  visual forms in this font, not a shaping bug.
- **Reph: standalone "र्" doesn't match at all.** It shapes to 2 glyphs
  (`uni0930` — र itself — plus `uni094D`, an explicit halant mark glyph),
  nothing resembling the single reph-hook shape found in §2.

**Verdict: standalone shaping is not usable as the ghost source for either
primitive** (confirmed, not assumed) — it would give the recorder a
plausible-looking but linguistically wrong reference for 30/37 consonants
and for reph entirely.

## Implication for Phase 1/3 (original, still holds under Noto)

Each half-form and the reph-hook atom's reference ghost must be **sourced
directly from one existing, already-shaped conjunct-pair cluster entry**
(e.g. `clusters["क"+virama+"ग"].glyphs[0]` for क's half-form ghost,
`clusters["र"+virama+"क"].glyphs[1]` for the reph hook) — any partner
works per §1/§2's identity findings (excluding the font's own current
exception pairs) — rather than a fresh standalone HarfBuzz shape. This
remains the technique `_build_contextual_forms()`/`_extract_ghost()` use,
unchanged by the font swap; only the specific exclusion set and per-font
data changed.

## Reproducing this check

`python/src/jayasree/strokes.py`'s `shape_word`, called directly against
the committed font (`NotoSansDevanagari-Regular.ttf` now, previously
`AnnapurnaSIL-Regular.ttf`), plus a straightforward groupby-and-compare
over `js/src/glyph-data.hi.json`'s already-shaped `clusters` table (no new
shaping needed for §1/§2 — that data already exists from Agent 3's
`_conjunct_inputs()` sweep). No new tool was added (one-off verification,
per this pass's scope, same as `shirorekha-report.md`).
