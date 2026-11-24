# Roadmap

Things worth doing that aren't done yet: not commitments, just a list so ideas don't get lost. When an item
is done, delete it here.

## Docs & discoverability

- **Live pipeline explorer on the Pages site.** The site shows the worked example as four static SVGs; a live
  version (a typed word, tabs to flip raw → centered → smoothed → straightened) is open.
- **Publish the Python package**, if ever worth it. `python/` is a build-time tool and deliberately unpublished.

## Smoothing

- **Fewer spurious hard corners.** Smoothed strokes still show more corners than expected. Corner detection
  uses a flat angle (`CORNER_ANGLE_DEG`, 50°) that ignores waypoint spacing, so a tight curve can trip it.
  On a 40-cluster sample, 60° cuts pieces per stroke from 2.45 to 2.00 with diminishing returns after.
  Next: try 60-65°; if that is not enough, make detection curvature-aware (angle per arc length); retune
  `rdp_epsilon` jointly. Needs a native writer's eye on before/after renders, not just a piece count.
  Regenerate from the existing raw data (`make process-strokes`); add a regression test when a change lands.
- **Clean Malayalam the same way as Hindi.** Hindi's strokes are rebuilt from the font's geometry
  (`jayasree.cleanup`). Doing the same for Malayalam would change its published output, so it needs the owner's
  approval, a visual review of every letter and a regenerated freeze golden (`CONTRIBUTING.md`, "Language
  freezes"). The cleanup was tuned on Noto Sans Devanagari; an attempt on Manjari and what blocks it are in
  `docs/MALAYALAM_CLEANUP_EXPERIMENTS.md`.

## Learning features

- **"Vanilla form" tooltips for fused clusters** (opt-in, e.g. `explain: true`). A learner meeting a fused
  conjunct such as ഴ്ച cannot see it is ഴ + ് + ച. A tap on a cluster would show its parts as glyphs, and
  `writer.explain(cluster)` would expose the data. Curated by cluster type (fused vowel signs, chandrakkala
  conjuncts), not per cluster. The decomposition comes free from the cluster's Unicode sequence; the only new
  data is a display-name table for marks.
- **Learn-the-letters add-on from the Central Hindi Directorate standard.** Its 2024 *Devanagari lipi evam Hindi
  vartani ka manakikaran*
  ([PDF](https://chd.education.gov.in/sites/default/files/devanagarilipiandhindivartanikamankikaran.pdf))
  has an official stroke-by-stroke chart for every letter (section 2.5), the alphabet and barakhadi tables and
  spelling rules. Possible uses: replay a letter as the chart's steps, spelling hints or quizzes, a trace mode
  that compares the learner's stroke order. Check its reuse terms before copying any image.
  See `docs/languages/hi/writing-rules.md`.
- **Constant pen speed.** The shared ease-in/out makes strokes slow-fast-slow. Hindi only, or both languages, is undecided.

## Multi-language support

Next in line, one at a time: Tamil, Telugu, Kannada, Bengali, Sanskrit (shares Devanagari with Hindi but needs
Vedic marks Hindi does not). The pipeline is `docs/LANGUAGE_ONBOARDING_AGENTS.md`; what each language needs is
content, not plumbing: a sourced character inventory, a verified font, a worklist, a native writer's recording,
and one `LanguageSpec` entry in `python/src/jayasree/languages.py`.

## Data & scale

- **Git LFS**, once the committed JSON grows to tens of MB (see `docs/CREATING_HANDWRITING.md`, "Data size &
  deployment").
- **Prune `glyph-data.json`** to the combinations that occur in real text instead of every combination
  HarfBuzz can produce. Needs a real-word corpus first.

## Deployment

The site deploys to GitHub Pages from `.github/workflows/pages.yml`. Open: cache headers or a CDN once there is
real traffic, and a custom domain if the github.io URL is outgrown.

## Bug-report → data pipeline

`tools/coverage_report.js` already reports each cluster as direct, composed or fallback, and can gate CI. Open:

- **A frictionless report → record loop.** Confirming a missing stroke and recording it still means typing the
  cluster into "Add custom cluster", recording, exporting and regenerating by hand. The report could end with
  the command that jumps straight to recording it.
- **Catch embedded-data staleness.** `build_standalone_recorder.py --check` hashes only the recorder's own
  files, so it reports "in sync" while the embedded `glyph-data.json` or `stroke-data.raw.json` is stale. The
  hash should cover the bundled data.

## Testing & tooling

- **Headless-browser tests for `index.js`'s DOM code** (`buildStage`, `traceSub`, `buildTracePath`). jsdom has
  no `getTotalLength()`, so the animation is only checked by hand in the demo. A Playwright test would close
  the gap, at the cost of a browser-binary dependency.
- **Ligature coverage for ു/ൂ/ൃ and the reduced la-form.** They fuse into a consonant-specific shape that generic
  mark composition cannot reproduce, so they are recorded as separate atoms (see `docs/ARCHITECTURE.md`,
  "Composition"). Revisit if it becomes visible.
