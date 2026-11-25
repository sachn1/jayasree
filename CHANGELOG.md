## v1.0.0 (2026-11-25)

### BREAKING CHANGE

- jayasree no longer bundles Malayalam data. Install @jayasree-stroke/ml (or /hi, /ml-font) and pass its glyphData and strokeData to load() and loadStrokes().

### Feat

- **js**: font-based Malayalam strokes, and the npm package split (1.0.0) (#79)
- **js**: publish the engine and each language's data as separate npm packages
- **js**: font-based Malayalam strokes, chosen per letter, with an outlineFallback option

## v0.8.0 (2026-11-23)

### Feat

- **js**: keep the pen at a constant speed for a headline script (#76)
- **js**: keep the pen at a constant speed for a headline script

### Fix

- **js**: draw a headline script's dots with their own letter and the headline last (#73)
- **js**: draw a headline script's dots with their own letter and the headline last

## v0.7.0 (2026-11-21)

### Feat

- Hindi (Devanagari) - recorded, cleaned and frozen (#70)
- **tools**: clean Hindi half-form and reph atoms (#61)
- **tools**: clean Hindi half-form and reph atoms against their contextualForms outline
- **py**: add an audit that ranks cleaned Hindi strokes by the bend the cleanup introduced (#59)
- **py**: add an audit that ranks cleaned strokes by the bend the cleanup introduced
- **tools**: enforce one-line docstrings for modules and classes too
- **tools**: make the docstring checker match real sections and handle generators and nested scopes
- **py**: clean Hindi strokes with the font's own geometry (#57)
- **tools**: fail the run when a Hindi cleanup falls back instead of hiding it
- **tools**: run the stroke cleanup by default for Hindi
- **tools**: add an opt-in, Hindi-only --cleanup stage to process_strokes
- **py**: add stroke cleanup that rebuilds a stroke from the font's own geometry
- **demo**: add a Hindi wordmark and show both on the landing page and README (#53)
- **js**: Hindi headlines, dots-last and conjunct vowel-sign placement (#51)
- **tools**: validate the markNudge on a glyph-data cluster
- **tools**: add real-shaped conjunct vowel-sign clusters and stem-last stroke order for Hindi
- **js**: draw dots last and give runtime-composed clusters their own headline and mark placement
- **demo**: show both wordmarks on the landing page and README, and match the colour in the demo
- **demo**: add the Hindi wordmark in a soft red
- **tools**: export a language's animated wordmark as one solid colour
- **demo**: draw a live Devanagari wordmark on the Hindi tab
- **demo**: one demo page with a tab per language
- **demo**: add Hindi demo
- **tools**: extend glyph-data build, stroke processing, validation and stroke recorder for Hindi
- **js**: runtime updates for Hindi composition
- **py**: extend ghost reference and geometry for Hindi recording
- **tools**: add a private build-extension hook for per-language research
- **py**: add $JAYASREE_DATA_ROOT override for non-primary languages
- **tools**: auto-load a language via ?lang=<code>, no file picker needed
- **tools**: save recorded strokes straight to the repo over Wi-Fi
- add a general-purpose code-reviewer subagent for this repo
- **tools**: wire contextual-form composition into the coverage audit and recorder
- **py**: mirror contextual-form composition in the offline stroke baker
- **js**: compose Devanagari half-form/reph clusters via contextualForms
- add named subagents for the language-onboarding pipeline
- **tools**: add coverage_report.js, a per-cluster direct/composed/fallback audit
- **js**: read chillu/split-vowel data from glyphData, not hardcoded tables
- **tools**: emit legacyEncodings/splitVowelParts into glyph-data.json
- **tools**: recognize candrabindu, nukta, and native-punctuation categories
- **tools**: validate every onboarded language's data files, not just Malayalam's
- **tools**: parametrize process_strokes.py by --lang, alias --preset=full
- **py**: add --lang to the CLI's alphabet command
- **tools**: parametrize build_glyph_data.py by --lang
- **py**: add language registry for multi-script tooling

### Fix

- **demo**: drop the cleanup-in-progress note from the Hindi tab
- **py**: make the audit handle arcs, empty paths and added limbs, and word its output as candidates
- **demo**: align the Hindi and Malayalam wordmarks (#55)
- **demo**: regenerate the Hindi wordmark with the aligned framing
- **tools**: frame the Hindi wordmark like the Malayalam one so the two line up
- **py**: raise clear errors for empty input in the cleanup instead of numpy ones
- **demo**: fill the Hindi wordmark in its ink color
- **tools**: handle an out_path outside ROOT in build_glyph_data's status print
- **demo**: detect the actual outbound IP instead of the hostname's
- **demo**: fall back to the next free port when the requested one is busy
- **tools**: make the stroke recorder's per-language text data-driven

### Refactor

- **tools**: drop the stem-last reorder for ख़ and ङ्ख (#65)
- **tools**: drop the stem-last reorder for ख़ and ङ्ख, the recorded order is kept
- **tools**: drop the cleanup flag; the language is the only switch
- **js**: extract the dot-size test so its thresholds are unit-tested
- **tools**: share one per-cluster processing function between main and its tests

## v0.4.1 (2026-10-05)

### Fix

- **py**: remove noqa no longer needed under ruff 0.15

## v0.4.0 (2026-07-23)

### Feat

- **data**: add ൻറ ground-truth glyph shape and composed stroke data

### Fix

- place prefix vowel marks correctly on chillu+consonant bases like ൻറ

## v0.3.0 (2026-07-17)

### Feat

- **demo**: add speech-to-text word input; load the wordmark as a static image

## v0.2.1 (2026-07-16)

### Fix

- **py**: pin Poetry venv to python/.venv via committed poetry.toml
- **js**: normalize legacy chillu encoding and compose prefix marks onto multi-glyph bases

## v0.2.0 (2026-07-15)

### Feat

- **tools**: give the stroke recorder a real ghost for missing matra
- publish jayasree to npm, add automated publish workflow
- repo rename, add more security
- remove site-verification html and instead use metadata in index
- add sitemap owenership verification and update package status
- update documentation, add sem-ver, github pages

### Fix

- **demo**: remove redundant animated logo from the demo page
- **js**: recursively resolve intermediate mark-chain glyphs and fix mark-vs-direct-match precedence
- **js**: render inter-word spaces and register a maatra  as a composable mark

## v0.1.0 (2026-07-13)

### Feat

- add the configurables to the UI
- add favicon
- add linters, makefile, docstrings, readme
- completed strokes and minor fixes to the rendition
- refine stroking with centering and straightening wrt ghost font, refine recorder ui, add logo and name, update readme
- add standalone support for tab for strokes
- add more character combinations, update the stroke-recorder html
- self-contained JS animator with bundled glyph data and stroke recorder
- initial malayalam-stroker monorepo

### Fix

- remove incorrect backslash from index.js

### Refactor

- add docstrings, split monolithic html files, add linters
