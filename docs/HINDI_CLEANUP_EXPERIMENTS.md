# Hindi stroke cleanup: what was tried

Why Hindi's strokes are rebuilt from the font's geometry, and what was learned getting there. The result is
described in `docs/ARCHITECTURE.md` ("Cleanup (Hindi)"); the code is `python/src/jayasree/cleanup/`. The older
centering and smoothing attempts are in `docs/CENTERING_EXPERIMENTS.md`.

## The problem

Centering and smoothing keep the hand's tremor. On a thick font (Noto Sans Devanagari) that shows as wavy
knots and junctions. Polishing the human's path could not remove it, because the tremor *is* the path.

## The idea

A recorded stroke carries two kinds of information. **Topology** (order, direction, where the corners are) only
the human can supply. **Geometry** (the exact curve through the ink) the font already knows. So keep only the
human's start, end and corners, and recover the curve from the font.

## Attempts, in order

1. **Fix the reference field first.** Two bugs in the distance field production used:
   - Counters (the hollow inside a loop) were painted as solid ink, so gradient ascent climbed toward empty space.
     Fixed with a nonzero-winding fill.
   - The raster stretched a w × h box onto a square, so "depth" was not true distance. Fixed with square pixels.

   Correcting only the field, with the old pipeline otherwise unchanged, cut the wiggles on 11 test letters from
   293 to 232.
2. **v1: follow the ridge.** Minimum-cost path through the field between the human's anchors (pinned at both ends,
   so it cannot jump branches, the failure that sank the old skeleton-snap attempts), smoothed, then fitted with a
   few cubic Beziers by least squares. *Approximation*, where the old `fit_piece` *interpolated* every waypoint,
   which is why tremor survived. Wiggles: 293 → 74. Still unnatural, for three reasons:
   - corners were trusted from the recording, and many sit on smooth curves (भ's curl);
   - the ink's centre line itself wiggles wherever the font's stroke width changes;
   - the stretched field (fixed in step 1).
3. **v2: the fairest path through the ink channel.** Corners are accepted only where the *font's* ridge turns
   sharply. The curve minimizes bending energy and curvature change while staying inside a fraction of the ridge's
   half-width: a bounded linear least-squares problem, convex, one answer, no tuning loop (an elastic band pulled
   through a channel). Wiggles: 74 → 26; every Hindi test letter ended at 0-2. Drift from the recording stayed
   small (9-18 font units for Hindi, 9-29 for Malayalam), so it is the same letter, not a replacement.
4. **Primitives first.** Dots and straight lines are recognised and made exactly, not traced:
   - A dot (under 70 units) becomes one point at the centre of the font's ink blob. If it sits inside a letter's own
     ink it is a stray pen tap, left as recorded and flagged (ष has one, 9 units).
   - A straight line becomes two points on the stem's centre, snapped to exact horizontal or vertical within
     4 degrees. A straight run inside a curve (ण's legs) becomes an exact line joined with a matching tangent.
   - Survey over every recorded stroke: Hindi 47 of 48 lines and 7 of 8 dots made exactly (42 snapped to H/V);
     Malayalam 98 of 98 lines. Recorded lines were already within about 1 degree on average (max 2.1 Hindi, 3.2 Malayalam), so the gain is
     exactness and consistency, not rescue.
5. **A stem drawn up then back down** (अ आ औ ख च) is a real 180-degree reversal, not a kink; it becomes two exact
   lines.

## Things that went wrong or surprised

- A min-cost route can silently skip a loop the human drew away and back. Routing waypoints fix it, and a
  recording-to-result distance in both directions exposes it.
- Parameters trade fidelity for smoothness: a wider channel and higher smoothness give a more relaxed curve that
  drifts further from the exact centre.
- The first audit sampler took about an hour; a vectorized one takes about 10 s over all 468 Hindi strokes.
- `scikit-image`'s path search was replaced by a small `min_cost_path` (matched it on 300 random grids, ties
  included), so no new dependency.

## Half-form and reph atoms

An audit ranking strokes by the bend the cleanup *introduced* (beyond what the human drew) showed that every
strongly wobbly stroke was one of the 39 half-form and reph atoms. They have no outline of their own, so the
cleanup had skipped them (up to 45 curvature flips, against at most 5 for cleaned atoms), and every conjunct
reuses them. Cleaning them against the font's half-form outline cut max flips from 45 to 4 and the mean from 12.5
to 0.3. Six strokes stayed flagged (श् झ् ग़् न् ...) for a look by eye. The audit ranks; it does not judge.

## Still open

- भ keeps a small kink where the curl meets the crossbar; it is in the recording and in the font.
- Bezier tolerance is tight (2 units), so segment counts are higher than v1; loosening it would shrink the file.
- The metrics are proxies. The bar is "looks like a real pen path over the font", judged by eye.
- Malayalam is not cleaned this way; doing so changes its published output (`docs/ROADMAP.md`).
