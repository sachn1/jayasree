# Malayalam stroke cleanup: what was tried and what blocks it

The Hindi cleanup (`jayasree.cleanup`, see `docs/HINDI_CLEANUP_EXPERIMENTS.md`) rebuilds each recorded stroke from
the font's own geometry. This is an attempt to do the same for Malayalam (Manjari), to remove the wobble that
remains in its strokes. It was run as an experiment on a copy of the data; Malayalam's shipped strokes are unchanged.
The work stopped here, with the obstacles below.

## What was run

1. The Hindi cleanup, unchanged, on all 291 recorded Malayalam atoms that have an outline. No cluster failed.
2. A second version: the stroke may stray at most 15% of the ink's half-width from its middle (45% before), circle
   fitting accepts looser rounds (16 font units, 70 degrees), and a cluster-level step makes strokes that are meant to
   meet actually meet (below).

## Results (594 strokes, shipped data against cleaned)

| Measure | Shipped | Cleaned |
|---|---|---|
| Strokes bending more than 25 degrees beyond the recording | 168 | 55 |
| Mean drift from the recording (font units) | 36 | 21 |
| Strokes with 16 or more curvature flips (81) | mean 32 | mean 2 |
| Strokes where the cleanup keeps the recorded path for a stretch | | 75 (in 66 atoms) |
| Gaps over 12 units between ends meant to touch (466 joins) | 202 | 3, after the join step |

The wobbliest strokes improve a lot. The rest is not clean enough to ship.

## Difficulties

- **Spirals and small loops.** Where a loop sits inside one blob of ink, the font's centre line collapses and the
  cleanup falls back to the recorded path. This is concentrated in the fused ൂ letters (about 25 atoms, up to 20% of
  a stroke) and a few conjuncts. The recorded loops are also not concentric with the font's spiral band, so the
  result does not close cleanly. It needs the spiral built from the font's own centre line.
- **Rounds are not circles.** Manjari's bowls and counters are ovals and teardrops. A circle fit that is strict enough
  to be exact misses most of them; one that is loose enough to catch them bends the letter. Exact rounds need ellipse
  or arc fitting, and closing loops the writer left almost shut.
- **Strokes that should meet do not.** Recordings leave gaps at junctions (a mean of 15 font units across 466 joins),
  and the cleanup works one stroke at a time, so it cannot see its neighbours. A straight link closes the gap but
  leaves a hook. What works is a cluster-level step: trim an overshoot at the crossing, extend a shortfall along the
  stroke's own direction, or curve in. Each join also has to be classified (T, corner, or a stroke that merges into
  another tangentially).
- **No reliable measure of "clean".** Curvature flips count noise on nearly straight lines, so strokes that look
  perfect score worse. Distance from the ink's middle came out near 12 units for every version, including the raw
  recording, so it could not show an improvement. Judging needs a person looking at each letter.
- **Composition.** About 60% of Malayalam's clusters are composed from the atoms, so changing an atom changes all
  of them. Every composed cluster needs the same review.
- **Frozen output.** Cleaning changes what Malayalam's visitors see. It needs the owner's approval, a letter-by-letter
  review and a regenerated freeze golden (`CONTRIBUTING.md`, "Language freezes").
- **Run time.** Each atom takes 3 to 20 seconds. Running workers in parallel with each worker using every core for its
  numeric libraries made it 50 to 100 times slower; pin each worker to one thread.

## What would be needed

Spiral construction from the font's centre line; ellipse and arc fitting with loop closing; the cluster-level join
step above, with join classification; a visual review tool for all 291 atoms and the clusters composed from them.
