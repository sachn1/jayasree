
# Jayasree (JS)

Animates Indic-script text (Malayalam and Hindi so far) as handwriting - a pen traces each letter left to right,
over a faint ghost of the complete letterform.

Self-contained. No server. No font file at runtime. Glyph shapes are
pre-computed and bundled in `glyph-data.json`.

## Install

```bash
npm install jayasree
```

Published at [npmjs.com/package/jayasree](https://www.npmjs.com/package/jayasree).
You can also copy `js/src/` into your project or serve it locally instead -
it's plain ES modules, no build step required.

## Usage

```js
import { createStrokeWriter } from "jayasree";

const writer = createStrokeWriter(document.getElementById("stage"));
await writer.load();          // fetches glyph-data.json once
await writer.loadStrokes();   // fetches stroke-data.json (no-op if absent)
await writer.play("നന്ദി");   // any text in a supported script, e.g. Malayalam or Hindi

writer.replay();   // play the same text again
writer.cancel();   // stop mid-animation
writer.destroy();  // cancel + clear the container
```

Spaces and common punctuation (`.`, `,`, `!`, `?`, `;`, `:`, `-`, quotes,
parens) work in `play()` text without any setup - they're rendered as
plain static characters, not animated handwriting, since they're not part
of any script's letterforms. See `UNIVERSAL_CHARS` in `index.js` for the
exact set.

Chillu letters (ൺ/ൻ/ർ/ൽ/ൾ/ൿ) work in `play()` text regardless of which of
the two valid Unicode encodings they use. A chillu can be written as one
atomic codepoint (`ൻ` = `U+0D7B`, the modern form) or as the legacy
3-codepoint sequence `consonant + ് (virama) + ZWJ` (`ന` + `്` + zero-width
joiner) - both render identically in every font, including real-world text
from WhatsApp, older keyboards, and many CMSs. `play()` normalizes the
legacy form to its atomic equivalent internally, so both spellings trace
the same stroke; you never need to normalize input yourself. See
`normalizeChillus()`/`LEGACY_CHILLU` in `index.js`.

## Options

`createStrokeWriter(container, options)` accepts:

| Option | Default | What it does |
| --- | --- | --- |
| `speed` | `6000` | Nominal pen speed, in font-units/second. Higher = faster trace. |
| `tighten` | `0.06` | Inter-cluster spacing tightening, as a fraction of `unitsPerEm` trimmed from each cluster's advance - the font's own advance widths read as a little loose for a handwriting UI. `0` reproduces the font's raw spacing. |
| `strokeWidth` | `0.022` | Ink line thickness, as a fraction of `unitsPerEm`. |
| `outlineOnly` | `false` | Ignore authored strokes entirely and always animate the outer-contour outline fallback - useful for a consistent tracing style independent of authoring coverage (e.g. a wordmark mixing authored and not-yet-authored clusters). |
| `glyphData` | `null` | Pre-loaded glyph data object, skipping `load()`'s own fetch. |

```js
const writer = createStrokeWriter(document.getElementById("stage"), {
  speed: 8000,       // faster pen
  strokeWidth: 0.03,  // thicker ink line
});
```

`play(text, playOptions)` and `replay(playOptions)` additionally accept:

| Option | Default | What it does |
| --- | --- | --- |
| `speed` | `1` | Speed *multiplier* for this call only (applied on top of the writer's own `speed`). `2` traces twice as fast. |
| `count` | `1` | Number of times to trace the word in a row, pausing briefly between repeats. A new `play()`/`replay()` call, or `cancel()`, stops the sequence before its next repeat. |

```js
await writer.play("നന്ദി", { count: 3 });   // trace it three times in a row
await writer.replay({ speed: 0.5, count: 2 }); // replay slower, twice
```

## Detecting approximated clusters

Not every cluster has (or can be composed from) recorded handwriting - when
one doesn't, `play()` falls back to animating the printed glyph's own outer
contour instead, which looks like tracing a border rather than real
handwriting. `getFallbackClusters()` returns which clusters from the most
recent `play()`/`replay()` call did this, so a caller can tell the user the
trace is only approximated for part of a word instead of silently rendering
a border-trace as if it were normal handwriting:

```js
await writer.play("ഖ്ര");
if (writer.getFallbackClusters().length) {
  // e.g. ["ഖ്ര"] - no authored stroke, and no composable mark recipe
  // (subjoined-ra) to build one from other recordings.
  showNote("Some strokes are approximated - handwriting for this exact letter combination isn't recorded yet.");
}
```

## Two data files

Both live in `js/` and should be committed to your repo:

| File | What it contains | Font-specific? |
|---|---|---|
| `src/glyph-data.json` | SVG outlines + advance widths for every cluster | Yes - re-run `tools/build_glyph_data.py` when you change fonts |
| `stroke-data.json` | Hand-authored centerline stroke paths | No - commit once, works across fonts |

When `stroke-data.json` has coverage for a cluster, the pen follows those
paths. Otherwise it falls back to tracing the outer contour of the font
outline.

## Regenerating glyph-data.json for a different font

```bash
cd python && poetry install
# defaults to the bundled Manjari-Regular.ttf:
poetry run python ../tools/build_glyph_data.py
# or supply your own:
poetry run python ../tools/build_glyph_data.py /path/to/MyFont.ttf
```

## Authoring stroke-data.json

Open `tools/stroke-recorder.html` in a browser, draw strokes over each ghost
glyph, and export. The output is keyed by Unicode cluster (`"ന"`, `"ക്ഷ"`).
Save it as `js/src/stroke-data.json` and commit.

## Configuring per-cluster behaviour

```js
import { createStrokeWriter, START_OVERRIDES, DIRECTION_OVERRIDES } from "jayasree";

// Where on the contour the pen starts (fallback mode only)
START_OVERRIDES["ന"] = "topmost";   // "leftmost" | "rightmost" | "topmost" | "bottommost" | 0..1 fraction
START_OVERRIDES["ക"] = ["leftmost", 0.1]; // per sub-contour array

// Which way around the contour the pen travels (fallback mode only)
DIRECTION_OVERRIDES["ന"] = "reverse";  // "forward" | "reverse"
```

## Styling

```css
.my-stage {
  --ms-ink-color:    #1a1a2e;   /* trace line */
  --ms-ghost-color:  #e0daf5;   /* faint letterform behind the trace */
  --ms-stylus-color: #e8b84b;   /* pen-tip dot */
}
```

`.ms-ghost` and `.ms-stroke` are the two CSS classes on the rendered SVG.
Skip the default `style.css` entirely and write your own if you prefer.

## License

MIT.
