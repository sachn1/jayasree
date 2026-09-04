# Test fixtures

`Manjari-Regular.ttf` is bundled here **only** so the test suite runs
deterministically offline, with zero network calls and zero ambiguity
about which font produced which test assertion. It is not a runtime
dependency of the package and is not distributed in the published wheel.

Manjari is designed by Santhosh Thottingal for Swathanthra Malayalam
Computing (https://gitlab.com/smc/fonts/manjari), licensed under the SIL
Open Font License 1.1 - see OFL.txt in this directory.

`AnnapurnaSIL-Regular.ttf` is Agent 2's proposed ghost font for Hindi
(Devanagari) - see `docs/languages/hi/font-report.md` for the full
candidate comparison and HarfBuzz coverage-verification results. It is
vendored here ahead of time (same offline-determinism rationale as
Manjari) but is **not yet wired into `languages.py`** - that, plus
`_chars_hi.py` and the `default_font` registry entry, is Agent 3's job,
gated on human approval of this font choice. Designed by SIL International
(https://github.com/silnrsi/font-annapurna), licensed under the SIL Open
Font License 1.1 - see AnnapurnaSIL-OFL.txt in this directory.
