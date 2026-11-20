# Using the JS library

The full guide to `createStrokeWriter`: loading, playing, every option, and detecting clusters
that fall back to an approximation. The README has the three-line version.

```js
import { createStrokeWriter } from "jayasree";

const writer = createStrokeWriter(document.getElementById("stage"));
await writer.load();          // fetches glyph-data.json once
await writer.loadStrokes();   // fetches stroke-data.json (optional, graceful no-op if absent)
await writer.play("നന്ദി");
```

```bash
npm install jayasree
```

Published at [npmjs.com/package/jayasree](https://www.npmjs.com/package/jayasree).
`.github/workflows/publish.yml` publishes future version bumps automatically
on a version tag push (or a manual run), authenticated via npm Trusted
Publishing (OIDC) - no token stored in this repo. Until the trusted publisher
is configured on npmjs.com, cut releases with `npm publish --access public`
from `js/`. You can still copy `js/src/` into your project or serve it
locally instead - it's plain ES modules, no build step required.

### Configurable options

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

### Detecting approximated clusters

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
