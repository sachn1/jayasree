# Shirorekha (headline) — structural verification

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
