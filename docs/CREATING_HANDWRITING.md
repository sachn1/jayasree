# Creating handwriting from scratch

How to take a font and a writer's pen to a working language: shape the font, record strokes,
process them, watch them animate. The README has the short version.

Step by step, starting from nothing but a font file. (If `glyph-data.json`
and `stroke-data.raw.json` already exist for your font - the common case -
skip to step 2.)

### 1. Generate `glyph-data.json` (once per font)

```bash
make install
make build-glyph-data FONT=/path/to/YourFont.ttf
```

Shapes the full Malayalam character inventory
(`python/src/jayasree/_chars.py`) through HarfBuzz and writes every
cluster's outline, advance width, and mark-composition recipe to
`js/src/glyph-data.json`. This is what supplies the ghost outline you trace
over in step 2, and what `stroke-data.json` gets centered/straightened
against in step 3. Re-run it whenever you switch fonts - see
"Using a different font" below for what does and doesn't carry over.

### 2. Record strokes

`stroke-recorder.html`'s dropdown defaults to a **reduced set** - only the
~290-ish atoms that genuinely need a hand-drawn stroke (standalone
characters, the vowel signs that fuse into consonant-specific shapes, and
true ligature conjuncts) - not the full ~2050 clusters `glyph-data.json`
covers, most of which compose automatically from those atoms (see
`docs/ARCHITECTURE.md`'s "Composition" section). Each entry is marked ✓ (recorded) or ○
(missing); a "⇥ Next missing" button jumps to the next gap. Check "Show all
clusters" to browse the full ~2050 (useful for spot-checking a composed
result against its ghost).

```bash
make build-recorder                # builds the offline copy, untracked: tools/stroke-recorder-standalone.html
                                   # (PROJECT_LANG=hindi -> stroke-recorder-standalone.hi.html)
open tools/stroke-recorder.html    # or open the standalone copy built above, offline
```

**With a ghost font (the normal case)** - the character is already one of
the atoms `glyph-data.json` covers:

1. Drop `glyph-data.json` into the recorder.
2. Pick a character from the dropdown - its ghost outline appears
   automatically, no setup needed.
3. Trace it in stroke order.
4. Load your existing `stroke-data.raw.json` (if any) to merge into it
   rather than starting over.
5. Export, and save the result over `js/src/stroke-data.raw.json`.

**Without a ghost font (blind)** - a combination outside the standard set
`build_glyph_data.py` generates, so it has no outline in `glyph-data.json`
at all. Two options:

- Add it to `build_glyph_data.py`'s input list and re-run step 1 so it gets
  a real ghost outline like everything else - preferred for anything meant
  to stay in the project, since centering/straightening (step 3) need a
  reference outline to work against.
- Or use the recorder's "Add custom cluster" field to draw it freehand with
  no outline to trace over. Useful for a quick one-off, but the result
  skips centering/straightening entirely (there's nothing to center or
  straighten against) - expect it to look rougher than a traced stroke.

### 3. Process

```bash
make process-strokes                       # Malayalam (the default)
make process-strokes PROJECT_LANG=hindi    # any other registered language
```

(The Python tools import `uharfbuzz`; run them inside the Poetry environment
- `cd python && poetry run python ../tools/process_strokes.py --lang hindi`
- if a bare `python3` doesn't have the dependencies.)

Centers each stroke against `glyph-data.json`'s outline (gradient ascent
onto the ink's centerline), smooths it (corner-aware spline fit), straightens
it against detected straight ghost edges, and composes any cluster still
missing a stroke from parts that do exist. Writes `js/src/stroke-data.json`
- the only stroke file `index.js` loads at runtime; `stroke-data.raw.json`
is never touched, so re-processing with different settings is always
possible without re-recording. Stages can be run individually if you want
to compare them - `python tools/process_strokes.py --help` lists
`--center`/`--smooth`/`--straighten`/`--expand`, each independently
toggleable. See `docs/ARCHITECTURE.md` for a worked example of each stage's
effect on a real stroke, or `docs/CENTERING_EXPERIMENTS.md` for why each
stage's algorithm works the way it does.

### 4. See it animate

```bash
make demo
```

Open http://127.0.0.1:8000/demo/ , pick a language tab (or go straight to `/demo/#hi`), and type the word.

### Using a different font

Are the hand-drawn strokes specific to Manjari (the font this project was
recorded against), or portable to any Malayalam font? They're centerline
traces of Manjari's letterforms, so in that sense yes - they're tuned to
Manjari's specific proportions, stroke count, and junction points. But
`process_strokes.py`'s centering and straightening stages re-fit each stroke
against *whichever* font's `glyph-data.json` you feed them: centering nudges
points onto the new font's ink, straightening re-aligns straight runs to the
new font's actual edges. So swapping fonts and re-running
`process_strokes.py` (no re-recording) pulls existing strokes toward the new
font's shape automatically - but only as far as a bounded nudge (see
`centering.py`'s `MAX_SHIFT_FU`); it won't invent a different stroke count
or fix a letterform that's structurally different from Manjari's.

- **Similar-style font**: regenerate `glyph-data.json` for it (step 1) and
  re-run `process_strokes.py` (step 3) - no re-recording needed.
- **Structurally different font** (e.g. one where a letter has an extra loop
  or a fundamentally different construction): expect to re-record the atoms
  that genuinely differ, and spot-check the rest against the new ghost.

### Data size & deployment

The library is fully static: `index.js` `fetch()`s `glyph-data.json` and
`stroke-data.json` at runtime, and nothing is built or generated
server-side - deploying is just serving `js/src/` (or your own bundle of it)
as static files. Both JSON files are committed to the repo and currently
small (low hundreds of KB combined); that's fine to check into git as-is.

If a second language's data gets added, or a much larger font's outlines
push the combined size into the tens of MB, plain git starts to get slow to
clone/diff. At that point, two options worth considering rather than
letting it grow unchecked:

- **Git LFS** for the JSON data files - keeps the repo itself small; git
  only fetches the actual blobs on checkout.
- **Split per-script** (`glyph-data.ml.json`/`stroke-data.ml.json`,
  `glyph-data.ta.json`/... for a hypothetical Tamil addition) so a page using
  one language doesn't fetch another's data. This is how it works now:
  Malayalam keeps the original unsuffixed files (`_chars.py`,
  `glyph-data.json`, `stroke-data.json`) and every other language gets
  `.{code}`-suffixed ones (Hindi: `_chars_hi.py`, `glyph-data.hi.json`,
  `stroke-data.hi.json`), all registered in `jayasree.languages`.
