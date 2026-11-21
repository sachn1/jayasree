# Test fixtures

`Manjari-Regular.ttf` is bundled here **only** so the test suite runs
deterministically offline, with zero network calls and zero ambiguity
about which font produced which test assertion. It is not a runtime
dependency of the package and is not distributed in the published wheel.

Manjari is designed by Santhosh Thottingal for Swathanthra Malayalam
Computing (https://gitlab.com/smc/fonts/manjari), licensed under the SIL
Open Font License 1.1 - see OFL.txt in this directory.

`NotoSansDevanagari-Regular.ttf` is Hindi's ghost font (Agent 2's approved
choice - `languages.py`'s `"hindi"` `default_font`). It is a **static
instance** (`wght=400 wdth=100`, i.e. Regular) extracted with
`fonttools varLib.instancer` from Google/Noto's variable-font distribution,
to match this project's single-static-TTF convention; instancing was
verified to give byte-identical HarfBuzz shaping to the variable source.
Why Noto over Annapurna SIL (the original pick, since removed from this
directory - its source and SHA-256 are in `docs/languages/hi/README.md`),
and the measurements behind it, are in that README's "Font decision".
Designed by the Noto Project Authors
(https://github.com/notofonts/devanagari), licensed under the SIL Open Font
License 1.1 - see NotoSansDevanagari-OFL.txt in this directory.
