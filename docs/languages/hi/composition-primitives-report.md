# Hindi (Devanagari) — Composition Primitives: Feasibility Verification

> **Status: verification complete, informs implementation.** This checks
> the premise behind `docs/languages/hi/labeling-worklist.md`'s "headline
> finding" — that Devanagari's half-forms and reph can each collapse to a
> small number of reusable recorded atoms, composed generically at
> runtime — against real shaped data from the committed
> `js/src/glyph-data.hi.json` and `AnnapurnaSIL-Regular.ttf`, before any
> runtime composition code is written. Same methodology as
> `shirorekha-report.md`: verify against real outlines first, don't assume.

## Conclusion

**The premise holds, for both primitives, with one small named exception.**
Every consonant's half-form is a single, reusable shape and the reph hook
is a single, reusable shape — but neither can be sourced by shaping the
trigger sequence standalone (the technique that worked for rakaar). Ghosts
must instead be extracted directly from an already-shaped conjunct-pair
cluster entry.

## 1. Half-form shape identity (in-context)

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

## 2. Reph hook shape identity (in-context)

`clusters["र"+virama+C2].glyphs[1].d` compared across all 40 reph pairs:
**100% identical, one single shape, zero exceptions.**

## 3. Standalone (word-final) shaping vs. in-context shape

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

## Implication for Phase 1/3

Each half-form and the reph-hook atom's reference ghost must be **sourced
directly from one existing, already-shaped conjunct-pair cluster entry**
(e.g. `clusters["क"+virama+"ग"].glyphs[0]` for क's half-form ghost,
`clusters["र"+virama+"क"].glyphs[1]` for the reph hook) — any partner
works per §1/§2's identity findings (excluding ड़्य/ढ़्य per §1's noted
exception) — rather than a fresh standalone HarfBuzz shape. This is a new
technique for `_standalone_inputs()`/the ghost-sourcing path (extracting
one glyph from an existing multi-glyph cluster entry, rather than shaping
a string directly), not previously needed for any of Malayalam's or
Hindi's other atoms.

## Reproducing this check

`python/src/jayasree/strokes.py`'s `shape_word`, called directly against
the committed `AnnapurnaSIL-Regular.ttf`, plus a straightforward
groupby-and-compare over `js/src/glyph-data.hi.json`'s already-shaped
`clusters` table (no new shaping needed for §1/§2 — that data already
exists from Agent 3's `_conjunct_inputs()` sweep). No new tool was added
(one-off verification, per this pass's scope, same as
`shirorekha-report.md`).
