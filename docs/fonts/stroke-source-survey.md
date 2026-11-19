# Stroke-source survey (Devanagari / Hindi)

Survey date: 2026-10-06. Scope narrowed (coordinator instruction) to
Devanagari; Chilanka / Manjari / Nupuram are included only as the reference for
what "has strokes" looks like. Scratch clones were made outside the repo.

Verdict legend: `strokes` = real pen-path / centreline data; `derived` =
strokes exist but were computed/fitted by someone from outlines (not authored
pen paths); `outlines-only` = nothing but closed filled outlines;
`could-not-verify`.

## Summary

| Candidate | Script | Licence | Verdict |
|---|---|---|---|
| Velthuis Devanagari (`devnag`, Metafont) | Devanagari | GPL (v. unspecified, "as published by the FSF") | **strokes** (real pen paths), but TeX-legacy forms, no Unicode mapping, no stroke-order guarantee |
| Tegaki bundle for Tillana | Devanagari + Latin | MIT code; Tillana OFL 1.1 | **derived** (auto-extracted centrelines, 75 codepoints) |
| Hindi-fish-game `lib/lekhan/hindiStrokes.ts` | Devanagari 42 letters | **No licence file** (all rights reserved by default) | **derived** (medial axis), unusable without permission |
| adhithyan15/coding-adventures `data/ductus/filmstrip-geometry.d/devanagari.json` | Devanagari 52 glyphs | No root licence found; project asserts CC BY-SA 4.0 for books/data | **derived** (hand-fitted to Noto from Commons panels / Lipi traces) |
| Wikimedia Commons "Devanagari X stroke order" | Devanagari 13 SVG + 72 GIF | CC BY-SA 3.0 (SVG checked) | **outlines-only** diagrams (order shown, no centrelines) |
| HP Labs India Lipi datasets (UNIPEN online traces) | Devanagari 111 chars, ~270 samples each | Research-only, no redistribution, no commercial use | `strokes` (real pen traces) but licence-incompatible; download not performed |
| Lipi Toolkit recognizer models | Devanagari | MIT | `strokes` (60-point resampled native-writer traces), reached only via the secondary source above; not opened directly |
| Noto Sans Devanagari | Devanagari | OFL | **outlines-only** |
| Annapurna SIL | Devanagari | OFL | **outlines-only** |
| Tillana (Google Fonts, ITF) itself | Devanagari | OFL | outlines-only (Tegaki's strokes are derived from it) |
| Hershey / single-line fonts | no Devanagari found | - | nothing found |
| Open Indic stroke-order dataset (KanjiVG/Hanzi Writer style) | - | - | nothing found |

## Reference: what "has strokes" looks like (Malayalam, SMC)

Opened real files (blobless clones of gitlab.com/smc/fonts/*):

- **Chilanka** `sources/svgs/` - 289 per-glyph Inkscape SVGs (e.g. `!.svg`,
  2000x2048 canvas). OFL 1.1 (`OFL.txt`, "Copyright 2023 The Chilanka Project
  Authors").
- **Manjari** `sources/svgs/` - 312 SVGs. OFL 1.1.
- **Nupuram** `sources/*.mp` (MetaPost: `pens.mp`, `glyph.mp`, `malayalam.mp`,
  `latin.mp`, plus 482 per-glyph `sources/glyphs/*.mp`). The OFL font; the
  shared MetaPost helper files are headed "Licensed under MIT License"
  (`sources/LICENSE.md` is MIT) - check each file's header before reuse.
- **Rachana, Meera, Keraleeyam** (`.sfd`): FontForge outline sources, no
  pen-path source in the repo -> outlines-only. Only the SFD top-level was
  checked, not every glyph.

## Devanagari findings

### 1. Velthuis Devanagari for TeX (Metafont) - verdict: strokes

- Source: CTAN `language/devanagari/velthuis.zip` (TeX Live package `devnag`),
  v2.17.1 README dated 2019-03-06. Downloaded and opened.
- Strokes: `mf/dnchars.mf` (138 KB, v2.12, (C) 1991-2005 University of
  Groningen, author Frans Velthuis, maintainers Anshuman Pandey / Kevin
  Carmody) defines ~318 `beginchar` glyphs by control points (`z5=...`) and
  `draw z5..tension1.4..z6..z7;`, i.e. genuine centreline paths, then a nib
  (`pickup pencircle xscaled thick yscaled thin rotated rot;` in `dndefs.mf`).
  Covers vowels, consonants, matras, conjunct halves ("half k.sa", "half bha"),
  numerals, virama, anusvara etc.
- Verified it runs: `mf` (TeX Live 2023) compiled `dvng10.mf` to a GF without
  error. Glyph shapes were not visually inspected.
- Licence: GPL; `dnchars.mf` header says "GNU General Public License as
  published by the Free Software Foundation" with no version; `doc/copying`
  is GPL v2 text. GPL is a copyleft licence - incompatible in spirit with the
  project's OFL-font stance; data derived from it would likely have to be
  GPL. Needs a human legal decision.
- Caveats (checked/observed): glyphs are named in Velthuis transliteration
  (`ka`, `.ta`, `'sa`), not Unicode; the `draw` order in source is
  construction order, not necessarily writing order; direction is the
  direction of the Metafont path, unvalidated; some glyphs have `alta`
  alternates (e.g. `front-a` original vs alternate: two drawings). The style
  is a Sanskrit/typographic printed form with the headline as separate
  frame/line elements (`frame;`/`aframe;`), not verified as textbook school
  forms. Many conjunct forms are TeX-style ligatures that do not match what
  HarfBuzz would produce from a Unicode font.
- Use: plausible seed for base-letter centrelines. Needs per-glyph review,
  Unicode mapping, order/direction correction (cf. Manjari ~35% reversed).

### 2. Tegaki (gkurt/tegaki) bundle for Tillana - verdict: derived

- Repo https://github.com/gkurt/tegaki (MIT). Opened
  `packages/renderer/fonts/tillana/glyphData.json` (175 KB; 164 keys, 75 of
  them Devanagari: independent vowels, consonants क-ह, nukta, matras, virama,
  chandrabindu, digits). Each glyph is a list of strokes with points
  `[x, y, width]`, a direction/order, plus metadata.
- This is computed by the project's skeletonisation pipeline
  (`packages/generator/src/processing/skeletonize/*`), not authored. Stroke
  counts look unlike textbook segmentation (क = 4 strokes, ख = 5, अ = 4 as
  extracted). No conjuncts, no half forms.
- Licence: Tegaki code MIT; bundled fonts carry their own licence. Tillana is
  OFL (verified in google/fonts `ofl/tillana/METADATA.pb`: designer Indian Type
  Foundry, license OFL, category DISPLAY). The glyphData derived from an OFL
  font is OK under OFL if attributed; Tegaki's repo has a root `LICENSE`
  (MIT); I did not find a per-font LICENSE for tillana (ems-allure and
  hershey-script have one).
- Textbook forms: Tillana is a display / calligraphic face, so the forms are
  stylised, not school forms. The README also notes Devanagari/Bengali headline
  is drawn as a separate word-level phase.

### 3. padhaipal/Hindi-fish-game `lib/lekhan/hindiStrokes.ts` - verdict: derived, unlicensed

- Opened. 298-line TS file: ordered polylines in a 0..100 box for the 42-letter
  varnamala. Header states shapes are "derived from the medial axis (skeleton)
  of the rendered Devanagari glyph" with order "following the ALfA charts
  (body -> danda -> head-line)". Headline is its own stroke.
- Licence: no LICENSE file in the repo and `gh api .../license` returns 404;
  `package.json` has no licence. Treat as all rights reserved; could be
  contacted. Useful as a reference for the order convention only.

### 4. adhithyan15/coding-adventures ductus data - verdict: derived

- Opened `code/learning/human-languages/data/ductus/filmstrip-geometry.d/devanagari.json`
  (456 KB; 52 glyph entries: vowels अ-औ, ऋ, consonants, ळ, a few matras). Each
  entry has `frames` of SVG markup, `penLifts`, and a `source` citation. Strokes
  are fitted against Noto Sans Devanagari outlines (`font:
  _fonts/NotoSansDevanagari-Static.ttf`). Citations are to Wikimedia
  Commons stroke-order SVGs (Saurmandal) and to HP Labs India Lipi
  recognizer prototypes (8 entries are Lipi-based).
- Format is SVG frames (stroke-order filmstrip) rather than a clean list of
  centreline polylines; extracting centrelines would need more work.
- Licence: no root LICENSE in the tree; `_assets/LICENSE.md` asserts CC BY-SA
  4.0 for authored books/data, and the data derives from CC BY-SA Commons
  files and MIT/research Lipi data. The repo looks heavily machine-generated;
  accuracy of the fitted strokes was not independently checked.

### 5. Wikimedia Commons "Devanagari X stroke order" - verdict: outlines-only

- Category lists 13 SVG (ऄ अ आ इ ई उ ऊ ऋ ए ऐ ओ औ झ) and 72 GIF files. Opened
  `Devanagari_अ_stroke_order.svg` (20 KB, Saurmandal, CC BY-SA 3.0): 35
  `<path>` elements; the black/grey/red paths are *filled outline pieces*
  (progressive build-up panels) and red filled arrow-heads; no centreline
  paths. Teaches order but is not extractable as pen paths. Only 13 letters.
  Licence is per file (CC BY-SA); GIFs not inspected.

### 6. HP Labs India / Lipi Toolkit online handwriting data - strokes, licence blocks

- HPL Isolated Handwritten Devnagari Character Dataset: 111 characters,
  ~270 samples each, >100 native writers, UNIPEN format (real pen-down/up
  traces, so real stroke segmentation and direction). Page: lipitk.sourceforge.net/datasets/dvngchardata.htm.
  Dataset licence (opened): research purposes only, no commercial use, no
  redistribution/reproduction. Not downloaded.
- LipiTk code and bundled recognizer models: MIT (reported by search results
  and by the ductus file's citation; I did not open the licence file myself).
- Verdict: cannot be committed to this repo. It could inform stroke order /
  direction conventions only (statistics, not data).

### 7. Outlines-only fonts (opened where stated)

- **Noto Sans Devanagari** (notofonts/devanagari, OFL): outlines-only; per the
  agent doc `sources/*.glyphspackage` `ka-deva.glyph` was opened earlier and is
  one closed outline. This session only listed the repo root.
- **Annapurna SIL** (silnrsi/font-annapurna, OFL): opened
  `source/AnnapurnaSIL-Regular.ufo/glyphs/D_evK_a.glif`: 5 closed contours,
  points only `line`/`curve` (no `move`), no centreline -> outlines-only.
- **Tillana** (google/fonts `ofl/tillana`): only compiled TTFs and metadata
  there; no source.
- **Ek Type (Anek Devanagari), ITF, Sarai, Tiro, Mukta, etc.**: could-not-verify
  at source level; the sources are normally Glyphs/UFO outline sources. I did
  not open them, so I only claim "no evidence of centrelines".

### 8. Nothing found

- Hershey fonts / single-line / pen-plotter fonts (singlelinefonts.com,
  Hershey Text, Relief SingleLine, EMS Allure, Hershey Script): none cover
  Devanagari in what I saw (Hershey Script and EMS Allure are Latin per
  Tegaki's README). Commercial single-line font vendors were not enumerated.
- KanjiVG / Make Me a Hanzi: CJK only. No Devanagari equivalent exists that I
  could find (GitHub search for "devanagari stroke order" returned no repos).
- No open Hindi writing-practice project with licensed, hand-authored data
  was found (Hindi-fish-game and coding-adventures are the nearest).
- `ctan` also lists Metafont fonts for other Indic scripts; not pursued
  because of the Hindi-only scope.

## Honest gaps

- Velthuis glyph appearance/order not inspected; the compile produced a GF
  only.
- Lipi datasets not downloaded; the "native pen traces" claim comes from
  the dataset page and the coding-adventures citations.
- Tillana-bundle stroke quality not visualised; stroke counts only.
- Search coverage is a web search plus a few GitHub searches, not exhaustive.
