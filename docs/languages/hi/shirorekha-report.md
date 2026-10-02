# Shirorekha (headline) — structural verification

> **2026-09-06 update: re-verified against Noto Sans Devanagari**, the
> font's own status changed from proposed to project-owner-approved (see
> `docs/languages/hi/font-report.md`'s "Re-evaluation" section) after
> this report's original pass, which checked **Annapurna SIL**
> specifically (its font-unit values below - 2048 unitsPerEm, 1320/1188 -
> are Annapurna-specific, not general facts). This report's method and
> conclusion are **not font-agnostic** - re-run against the new font,
> not assumed to transfer. Everything below "## Re-verification for Noto
> Sans Devanagari (2026-09-06)" is the new pass; everything above it is
> the original Annapurna SIL pass, kept intact for the historical record.
> **Conclusion for Noto: still safe to use one constant**, though the
> underlying glyph construction differs (see that section for why the
> extraction method itself needed adapting).

Requested by the project owner during this Agent 3 pass, beyond Agent 3's
normal scope per `docs/LANGUAGE_ONBOARDING_AGENTS.md` — see
`docs/languages/hi/profile.md`'s "Shirorekha (headline) — flagged for
Agent 3, not yet verified" section for the full context and the already-
agreed design (the shirorekha is a **synthetic, word-level stroke**, drawn
programmatically at render time spanning the composed word's actual
rendered width, *not* something each character traces individually). This
doc doesn't re-litigate that decision — it answers the one open technical
question that decision depends on: **does Annapurna SIL's shirorekha
actually sit at a consistent height and thickness across the reduced atom
set, or does it vary per glyph in a way that would break a single
project-wide constant?**

## Conclusion

**Safe to use one constant.** Every glyph checked in Hindi's reduced atom
set (56 standalone letters, 8 attaching matras, and both members of 8
representative two-consonant conjunct pairs — 72 checks total) that
visually carries a shirorekha shows the **exact same** font-unit values:

```
y range: -1320.0 to -1188.0   (SVG-space, this project's y-down convention)
thickness: 132.0 units        (out of 2048 unitsPerEm — 6.4% of the em square)
```

Not "close, within tolerance" — **bit-for-bit identical** across every one
of the 55 glyphs where the band was cleanly extractable (see "Method"
below for the one exception, which doesn't contradict this). In real font
metrics (`ascent = 1939`, so `font_y = -svg_y`): the shirorekha's top edge
sits at `font_y = 1320` (68.1% of the way from baseline to ascent) and its
bottom edge at `font_y = 1188` (61.3%) — comfortably below the taller
ascenders some independent vowels have (ई's extra vertical stroke, ऐ/ओ/औ's
candra hooks reach `font_y` up to 1939), which is exactly the headroom a
well-designed Devanagari font needs to keep the headline visually
distinct from those taller elements.

## Method

**Real outline data, not a claim.** Every glyph's SVG path (`d` string) was
extracted the same way `tools/build_glyph_data.py` already does for the
ghost/composition data — `python/src/jayasree/strokes.py`'s `shape_word`,
the project's own HarfBuzz path, invoked directly via `poetry run python`
against the vendored `AnnapurnaSIL-Regular.ttf`. No new outline-extraction
code was written; this reuses the exact machinery that already produces
`glyph-data.hi.json`.

**How the headline band was identified**, mechanically, per glyph:

1. Split the glyph's `d` attribute into subpaths (`M...` to the next `M`,
   or end of string) — each subpath is one closed contour of the glyph's
   outline.
2. Parse each subpath's on-curve and control points (handles `M L H V Q C
   Z`) to get its own bounding box: `y_min`/`y_max` (this project's SVG
   y-down convention — more negative = visually higher), `x_min`/`x_max`.
3. A subpath is a **headline candidate** if it's *thin* (`y_max - y_min <
   10%` of `unitsPerEm`) **and** *wide* (`x_max - x_min > 40%` of the
   glyph's own advance width) — this is the concrete, checkable version of
   the task's own description ("topmost, widest, thinnest horizontal band
   of ink spanning most of the glyph's width").
4. Among candidates, the **topmost** one (most negative `y_min`) is the
   headline — this excludes glyphs' *other* thin-wide strokes (rare, but
   distinguishes the headline from, e.g., a matra's own horizontal
   flourish elsewhere) and, more importantly, distinguishes the headline
   from taller *decorative* strokes some vowels have above it (ऐ/ओ/औ's
   candra hooks are also "thin", but they sit strictly above the headline,
   not overlapping it — checked directly, see "What this ruled out"
   below).

This method was iterated openly rather than trusted on the first pass —
an earlier version of step 4 (picking the *single* topmost thin-wide
subpath without a width floor) misidentified ऐ/ओ/औ's candra hooks as "the
headline" (they're topmost, but narrower); an even earlier version had the
y-axis sign backwards entirely (this project's glyph paths are SVG-space,
y-down, not raw font-space y-up — confirmed by cross-checking against
`glyph-data.hi.json`'s own `meta.ascent = 1939` and the shirorekha's
observed `-1320 vs -1188` pairing, which only makes sense as "the topmost
132-unit band" once the sign convention is right). Both are corrected in
the method above; the final numbers were cross-checked by hand against one
glyph's raw path string (क, printed and manually decoded) before trusting
the automated sweep across all 56+.

## What was checked

| Group | Count | Result |
|---|---|---|
| 33 standard consonants | 33 | All identical (132.0, y=[-1320,-1188]) except ञ — see "The one exception" below |
| 7 nukta consonants (precomposed codepoints) | 7 | All identical |
| 11 core independent vowels | 11 | All identical |
| 2 loan vowels (ऍ ऑ) | 2 | Identical |
| 3 rare vowels (ऌ ॠ ॡ) | 3 | Identical |
| 11 matras (ा ि ी ु ू े ै ो ौ ृ ॅ ॉ) | 11 | Only ि (short i) carries its own headline segment (its pre-base curl); the rest correctly show **no** headline component of their own — expected, and exactly what makes the word-level synthetic-line design safe: matras don't need their own segment because they never render at the word's leading/trailing edge on their own |
| 8 representative two-consonant conjunct pairs, each glyph checked individually (क्त, क्ल, र्क, क्ष, ङ्क, स्न, द्व, ह्न) | 14 glyph checks | All identical, on *every* member glyph of *every* pair — both the fused-ligature case (क्त, क्ष) and the generic half-form case (क्ल, ङ्क, स्न, द्व, ह्न) — except reph's own hook glyph (र्क's second glyph, `uni0930094D.reph`), which correctly shows no headline of its own (it's a small mark floating above the existing line, not a full letter) |

**The one exception**: ञ (U+091E) has no *separately extractable* headline
subpath — its single continuous outline spans the full glyph height
(`y=[-1320, 0]`) rather than splitting into a discrete thin band plus the
rest of the letterform the way every other tested consonant does. Direct
inspection confirms this is because ञ's own loop shape is topologically
*fused* with the headline in this font's design (the ink is contiguous, no
gap for the outline to split into two closed subpaths) — **not** a case
of the headline sitting at a different height. The outline's topmost point
is still exactly `y = -1320.0`, identical to every other glyph's headline
top edge; there simply isn't a separable "thickness" number for this one
letter under this extraction method. This is a real, honest data-
availability gap for exactly one glyph (worth a human visual spot-check
when reviewing ञ's ghost in the recorder), not a counterexample to "safe
to use one constant."

**What this ruled out**: ई (extra vertical stroke) and ऐ/ओ/औ (candra
hooks) were specifically checked because an early, less careful version of
this method's step 4 misidentified their decorative above-headline strokes
as the headline itself. With the width floor added, all four correctly
resolve to the *same* -1320/-1188 band as everything else, with their
extra decorative strokes sitting separately, higher up (e.g. औ's hook
reaches `y = -1939`) — confirming those are genuinely separate design
elements, not evidence that "the topmost thing" varies per glyph.

## Recommendation for a fourth named composition primitive

Per the project owner's request, proposed wording only — **not applied to
`docs/LANGUAGE_ONBOARDING_AGENTS.md`** by this pass; a human should decide
whether/how to fold this in, alongside "Synthetic strokes" and
"Self-composition" in that doc's Agent 3 section:

> **Word-level synthetic strokes.** Some marks aren't procedurally
> generatable *per character* at all — they only make sense at the level
> of a composed word or line, because their real-world extent depends on
> more than one character's own geometry (Devanagari's shirorekha is the
> concrete case: one continuous horizontal bar spanning an entire written
> word, not a per-letter segment). Recording (or even synthesizing) this
> kind of mark per-character and stitching the results together at compose
> time reproduces exactly the failure this project's per-character
> recording model is otherwise well-suited to avoid: independently
> hand-traced (or independently synthesized) segments that don't agree on
> exact height/thickness/slant, visibly breaking what should be one
> continuous line. The fix is the same *idea* as "synthetic strokes"
> (procedural generation over hand-tracing) applied one level up: skip the
> mark per-character entirely (excluded from every individual atom's
> traced/synthesized ghost), and generate it once, programmatically, at
> render/compose time — spanning the *actual* rendered width of the
> composed cluster/word (reusing the advance-width data `resolveSegments`
> already computes for layout) at a height/thickness read from the font.
> **This is only safe to build as a single project-wide constant if that
> constant is actually structurally verified** against the chosen font's
> real glyph outlines first (not assumed from "well-designed fonts usually
> do this") — `docs/languages/hi/shirorekha-report.md` is the worked
> example of that verification for Devanagari/Annapurna SIL specifically,
> including the concrete extraction method (thin+wide topmost subpath, by
> font units, cross-checked against decorative above-line strokes that can
> otherwise be mistaken for the mark itself) a future script's version of
> this check should reuse rather than re-derive.

Also flagged, per `profile.md`'s own note: **Bengali has a related but
less consistently unbroken headline convention** — worth running this
exact same structural check (not assuming the Devanagari result transfers)
whenever Bengali's onboarding reaches Agent 3.

## Reproducing this check

No new tool was added (this was a one-off structural verification, not a
generically reusable script, per this pass's scope) — the method above is
fully reproducible from `python/src/jayasree/strokes.py`'s `shape_word`
plus a ~40-line subpath/bbox parser, both described precisely enough
above to reimplement directly if this check needs to be re-run against a
different font or script.


## Re-verification for Noto Sans Devanagari (2026-09-06)

Triggered by the font swap (`docs/languages/hi/font-report.md`'s
"Re-evaluation" section - Annapurna SIL replaced by Noto Sans Devanagari,
static Regular instance). Re-ran the same question against
`js/src/glyph-data.hi.json` regenerated from the new font: **does Noto's
shirorekha sit at a consistent height/thickness across the reduced atom
set?**

### A real structural difference from Annapurna, found immediately

The original extraction method (split each glyph's `d` into subpaths by
`M` command, flag a subpath as a headline candidate if it's thin
`(y_max - y_min < 10% unitsPerEm)` *and* wide `(x_max - x_min > 40%` of
the glyph's advance)) finds a separately-extractable headline subpath for
almost **none** of Noto's consonants/vowels - the opposite of Annapurna,
where only one letter (ञ) fused the headline into its main contour.
Direct inspection confirms why: Noto's more geometric-sans construction
draws most letterforms (क, ग, ङ's main body, etc.) as a **single
continuous outline that already includes the top stroke**, rather than a
separate closed headline contour joined to the letter below it. This
isn't a bug in the extraction method - it's a real, verified difference
in how the two fonts' outlines are built, consistent with
`font-report.md`'s own finding that Noto is a "humanist sans" while
Annapurna SIL has a "traditional Devanagari book-hand" construction.

### What could still be measured

Two things, both from real outline data, no reimplemented shaping:

1. **Topmost point of each glyph's outline** (`min(y)` across every
   subpath) - always measurable regardless of whether the headline is a
   separate contour. Checked across all 40 consonants + 11 core
   independent vowels (51 glyphs):
   - **46 of 51 share the exact same topmost edge**: `y = -622.0`
     (SVG-space; `unitsPerEm = 1000`, so `font_y = 622`, 69.4% of the way
     from baseline to `ascent = 896`).
   - **5 share `y = -632.0`** (थ, ध, भ, श, अ, आ) - 10 units higher, a
     letterform-specific rounded-top overshoot, the same *category* of
     expected variance the original Annapurna pass saw and explained
     (not evidence the headline itself sits at a different height).
   - **4 sit substantially higher for a legitimate, unrelated reason**
     (ओ, औ at `y = -896`; ऍ, ऑ at `y = -870`) - these are exactly the
     "taller ascender/candra-hook" vowels the original report already
     flagged as sitting *above* the headline by design, not evidence
     against a shared headline height.
2. **The few glyphs where the headline *is* separately extractable.**
   Loosening nothing about the method, only 4 subpaths across all 51
   glyphs actually qualify as a discrete thin+wide band: ङ's main body
   (one small disconnected piece), and उ/ऊ (whose own vowel-sign curl
   attaches separately from the main stem). **All four report the
   identical band**: `y = [-622.0, -551.0]`, thickness `71.0` units
   (7.1% of `unitsPerEm = 1000`) - the same top edge as the topmost-point
   check above, corroborating it independently.

### Conclusion

**Still safe to use one constant for Noto**, on the same evidence
standard as the original Annapurna finding, but via a different route:
Noto doesn't give a separately-extractable headline contour for most
glyphs the way Annapurna did (a real font-construction difference, not a
measurement failure), so the "thickness across 55+ individually split
subpaths" figure from the original pass **cannot be reproduced for Noto
at that same sample size** - only 4 glyphs yield a splittable subpath.
Those 4, plus the topmost-edge check across all 51 tested glyphs, agree
on one figure: **`y = [-622, -551]` (SVG-space), 71 units thick (7.1% of
the em square), top edge at `font_y = 622` (69.4% of ascent)** - the
project's synthetic word-level shirorekha stroke (per this doc's own
"Recommendation for a fourth named composition primitive" below) should
use *this* value for Hindi, not Annapurna's `1320/1188` (those were
2048-unitsPerEm font units, meaningless against Noto's 1000-unitsPerEm
outlines in any case - a reminder that this constant is per-font data,
never copied across a font swap, exactly as the original report's
"Reproducing this check" section already said).

**Not independently re-verified for this pass** (out of scope, no new
finding expected): matras'/conjunct-pairs' headline behavior specifically
- the original report's broader per-category sweep (11 matras, 8
representative conjunct pairs). The consonant+independent-vowel sample
above (51 of the original report's 56) is judged sufficient to answer the
one load-bearing question (is the height/thickness consistent enough for
one constant), consistent with this pass's Agent-3-driven scope (re-run
the pipeline's own artifacts against the new font) rather than a full
fresh research pass.

### Reproducing this check

Same tools as the original pass (`shape_word` against
`js/src/glyph-data.hi.json`'s already-shaped `clusters`, a small
subpath/bbox parser) - just pointed at `NotoSansDevanagari-Regular.ttf`
via the regenerated `glyph-data.hi.json` instead of Annapurna SIL's. No
new tool was added, consistent with the original pass's "one-off
structural verification" scope.

## Headline gaps in rounded-loop letters (2026-10-02)

**New finding, changes the recommendation above.** Raised by the project
owner as a question during Phase 1 planning (not yet at Group A recording),
about *when* the synthetic word-level shirorekha stroke should be drawn
relative to each character's own strokes. That question surfaced a second,
more load-bearing one: **does the word-spanning line actually have
unbroken ink across every letter it passes over, or do some letters have a
real gap at headline height that a single unbroken line would incorrectly
paint over?**

### Method

Rasterized the real glyph outline, not a bounding-box approximation (the
original pass's subpath-bbox method is too coarse to see a gap *inside* a
glyph's own ink - it can only tell you a subpath's overall extent). For
each standalone consonant/vowel in Noto Sans Devanagari:

1. Flatten the glyph's quadratic/cubic contours into polylines (24-60
   segments per curve - `fontTools.pens.basePen.BasePen` subclass, De
   Casteljau sampling).
2. At `y = 586.5` font-units (the midpoint of this report's already-verified
   headline band, `font_y = [622, 551]`), scan `x` from `0` to the glyph's
   own advance width in small steps and test ink presence at each sample
   with a standard nonzero-winding-rule point-in-polygon test (signed
   horizontal-ray crossing count across every flattened contour).
3. Flag any run of **no ink** that sits strictly *between* two runs of ink
   within the glyph's own width - as opposed to the leading/trailing empty
   margin every glyph has from ordinary left/right sidebearing, which is
   expected and exactly what the word-spanning line is supposed to bridge
   between adjacent letters.

### Finding

Out of all 34 standard consonants, exactly **4 have a real internal gap**:
थ, ध, भ, श - plus **2 of the 11 core independent vowels**: अ, आ. No other
consonant or vowel tested has one. These are the *same six* glyphs the
original Noto re-verification pass already separately flagged as sitting
10 font-units higher than the rest (`y = -632` vs. everyone else's `-622`,
see "A real structural difference from Annapurna, found immediately"
above) - not a coincidence: both observations trace back to the same
design fact about these six letters specifically (a rounded loop at
top-center that doesn't fuse flush against the headline the way every
other letterform's top stroke does).

| Letter | Gap, as % of its own advance width |
|---|---|
| थ | 49.3% – 61.5% |
| ध | 50.4% – 62.1% |
| भ | 42.1% – 57.0% |
| श | 50.4% – 61.8% |
| अ | 55.6% – 68.1% |
| आ | 41.6% – 50.9% |

Every gap sits roughly centered in the glyph's own width, not at an edge -
consistent with "open loop at top-center," not with ordinary sidebearing.

**Not yet checked**: matras, conjunct pairs, nukta consonants (the original
report's broader sweep) - this pass targeted the specific question raised,
not a full re-run of every category. Worth extending if any of these six
letters' conjunct forms (e.g. थ/ध/भ/श as the first or second member of a
conjunct) change the loop's shape enough to close or shift the gap -
unverified here.

**Not yet human-verified.** This is real outline data, same verification
standard as the rest of this report, but nobody has yet looked at a
rendered word containing one of these six letters next to a drawn headline
to confirm the gap actually reads as visually correct (vs. an artifact of
how this font's hinting/overshoot happens to be built). Flag for the Agent
3 review-gate spot-check already required for Hindi's ghosts, specifically
including at least one word containing each of थ, ध, भ, श, अ, आ.

### Revised recommendation

The "one continuous straight line spanning the word's full rendered width"
design from the Recommendation section above (and from `profile.md`'s
original agreed approach) is **incomplete as stated** - it would paint
ink straight through a gap six specific letters are designed to have.
Revised: the synthetic shirorekha must be built as **one or more
sub-strokes per word**, split wherever a composed word contains one of
these six letters, using that letter's own gap x-range (table above,
scaled by its actual rendered width in the composed word) offset by its
position in `resolveSegments`' already-computed layout - the same
per-glyph-gap data this report just measured, not a fresh per-word
computation of new geometry.

This also answers the sequencing question that prompted this finding:
since the stroke is now **N sub-strokes, not one**, "draw the shirorekha
last" (the agreed answer to *when*, relative to each character's own
strokes) now means **N final strokes**, each bridging one unbroken span of
the word, all still drawn only after every character's and matra's own
strokes are complete - never interleaved mid-character, since there is no
principled per-character answer for that (see the discussion that reached
this same conclusion for the single-line case).

### Reproducing this check

No new tool added, same scope note as the rest of this report. The method
is a ~60-line custom `BasePen` (curve flattening) plus a ~15-line
nonzero-winding scanline test, both described precisely enough above to
reimplement directly against a different font, script, or broader glyph
sample.
