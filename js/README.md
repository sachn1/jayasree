
# Jayasree (JS)

Animates Malayalam text as handwriting - a pen traces each letter left to right,
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
await writer.play("നന്ദി");   // any Malayalam Unicode text

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
