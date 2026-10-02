# Test fixtures

`Manjari-Regular.ttf` is bundled here **only** so the test suite runs
deterministically offline, with zero network calls and zero ambiguity
about which font produced which test assertion. It is not a runtime
dependency of the package and is not distributed in the published wheel.

Manjari is designed by Santhosh Thottingal for Swathanthra Malayalam
Computing (https://gitlab.com/smc/fonts/manjari), licensed under the SIL
Open Font License 1.1 - see OFL.txt in this directory.

`AnnapurnaSIL-Regular.ttf` was Agent 2's **original** proposed ghost font
for Hindi (Devanagari) - see `docs/languages/hi/font-report.md` for the
original candidate comparison and HarfBuzz coverage-verification results.
Kept vendored for the record (its coverage/conjunct data is still valid
and referenced by the report), but **superseded** by
`NotoSansDevanagari-Regular.ttf` below, per that same report's
re-evaluation section - no longer `languages.py`'s `"hindi"` entry's
`default_font` (that now points at the Noto fixture below). Designed
by SIL International (https://github.com/silnrsi/font-annapurna),
licensed under the SIL Open Font License 1.1 - see AnnapurnaSIL-OFL.txt
in this directory.

`NotoSansDevanagari-Regular.ttf` is Agent 2's **approved** ghost font for
Hindi, after a re-evaluation pass triggered by a new font-choice
criterion (low stroke-width contrast / monoline ductus, since this
project's centering algorithm is unreliable near corners/junctions and a
calligraphic font multiplies those) - see `docs/languages/hi/font-report.md`'s
"Re-evaluation" section for the full comparison, quantitative
stroke-width-contrast measurements, and HarfBuzz coverage-verification
results. This is a **static instance** (`wght=400 wdth=100`, i.e.
Regular) extracted with `fonttools varLib.instancer` from Google/Noto's
variable-font distribution, to match this project's single-static-TTF
convention (same as Manjari/Annapurna SIL) - instancing was verified to
produce byte-identical HarfBuzz shaping output to the source variable
font across every atom/conjunct test in the report. **Wired into
`languages.py`** as the `"hindi"` `LanguageSpec`'s `default_font` -
`js/src/glyph-data.hi.json` was regenerated against it, and
`docs/languages/hi/labeling-worklist.md`,
`docs/languages/hi/composition-primitives-report.md`, and
`docs/languages/hi/shirorekha-report.md` were all re-verified against it
(Agent 3's re-run, per that font-report's approval). Designed by the Noto
Project Authors (https://github.com/notofonts/devanagari), licensed under
the SIL Open Font License 1.1 - see NotoSansDevanagari-OFL.txt in this
directory.
