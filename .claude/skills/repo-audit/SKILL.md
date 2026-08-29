---
name: repo-audit
description: Comprehensive, read-only, whole-repo health audit of jayasree - code quality, NumPy-style docstring compliance, demo functionality, data-file integrity, JS/HTML/workflow correctness, doc freshness, test coverage, and dependency hygiene. Produces a single prioritized report for the maintainer to triage. Manually triggered - use for a periodic health check or pre-release review, not for reviewing one PR's diff (use /code-review for that).
---

# Repo Audit

A full-repository, read-only audit - not a diff review. Inspect the repo as
it stands on the current branch and report every finding worth the
maintainer's attention, ordered so they can triage without reading the
whole thing. **Do not fix anything, do not edit files, do not commit** -
report only. The maintainer decides what to fix now, defer, or split into
separate tasks.

Work through every section below. Each section names concrete commands/greps
to run and what "wrong" looks like for this specific repo - don't skip a
section because it seems clean at a glance; run the check.

## 1. Automated gates (run first - cheapest signal)

```bash
make ci        # everything CI runs, both languages
make validate-data
```

Anything failing here is close to an automatic P0/P1 - if `make ci` isn't
green, that supersedes most manual findings below.

## 2. Docstring compliance (Python)

This project's specific convention (`pyproject.toml`'s
`[tool.ruff.lint.pydocstyle]` sets `convention = "numpy"`, and
`CONTRIBUTING.md` narrows it further):

- **Modules, classes, and private functions** (leading underscore): a
  single-line summary docstring. No Parameters/Returns sections needed.
- **Public functions**: one-line summary, then `Parameters` and `Returns`
  sections in NumPy format (even if it feels obvious from the signature).

Check `python/src/jayasree/*.py` and `tools/*.py` by hand for this exact
split - `ruff`'s `D` rules catch *missing* docstrings and basic format, but
not "a private function that grew a full Parameters block it doesn't need"
or "a public function with only a one-liner." Both are worth flagging as
style findings even though CI won't catch them.

## 3. Code quality & redundant dependencies

- `ruff check .` / `eslint js/src tools/*.js demo/*.js tests/*.js` for
  anything suppressed with an inline ignore/noqa that's no longer justified.
- Dead code: exported JS functions with no importer (`grep -rn "export function"
  js/src/index.js` cross-referenced against usage in `demo/`, `tests/`), unused
  Python functions/modules not referenced by `cli.py`, `tools/*.py`, or tests.
- Unused dependencies: diff `python/pyproject.toml` / `package.json` against
  actual imports (`grep -rn "^import\|^from" python/src` and JS `import`
  statements) - flag anything declared but never imported.
- Redundant or overlapping tooling (e.g. two libraries doing the same job).

## 4. JS runtime (`js/src/index.js`)

- JSDoc coverage/format consistency - this file already has a strong,
  consistent JSDoc style (one-line summary, `@param`/`@returns`, `{@link}`
  cross-refs for non-obvious control flow); flag any newer function that
  drifted from it.
- Any function whose docstring describes behavior the code no longer
  matches (comments rot faster than code - cross-check a sample of the
  more elaborate docstrings, e.g. `composeMark`, `resolveSegments`,
  `tryComposeStroke`, against their current implementation).
- Unhandled edge cases in the composition/segmentation functions
  (`resolveSegments`, `composeMark`, `applyMarkStroke`, `tryComposeStroke`,
  `tryComposeFromCharacters`) - these are the highest-complexity, highest-risk
  code in the repo; a subtle bug here silently mis-renders real words (see
  `docs/ARCHITECTURE.md` for prior examples of exactly this class of bug).

## 5. Data files (`js/src/*.json`)

- `python3 tools/validate_data.py` (already run in step 1, but re-confirm
  the cluster counts it prints look sane, not e.g. suspiciously low).
- Cross-check `js/src/stroke-data.raw.json` (hand-authored, source of truth)
  against `js/src/stroke-data.json` (processed) - every raw cluster should
  survive into the processed file (validate_data.py's cross-check covers
  this, but confirm it actually ran, not just parsed).
- `python/tests/test_data_snapshot.py` - passing means recorded data wasn't
  silently altered since the last approved snapshot. If it's failing,
  that's a P0 (see CONTRIBUTING.md's "Data integrity & governance").

## 6. Tests up to date

- Any recently-changed source file (`git log --since="90 days ago" --name-only
  -- python/src js/src`) with no corresponding test change nearby - possible
  coverage gap.
- Python coverage: `make test-py` and check it hasn't dropped from ~95%
  (CONTRIBUTING.md's stated baseline).
- Vitest: confirm `tests/index.test.js` and `tests/composition-coverage.test.js`
  still cover every exported/composition-relevant function in `index.js` -
  a new function with no corresponding test block is a gap.

## 7. Demo & HTML

- `make demo`, open it, type a few words spanning: a simple consonant+vowel,
  a conjunct, a chillu, and (if present) a known-tricky case like ൻറെ. Watch
  for console warnings (`jayasree: no glyph data for ...`) and obviously
  broken rendering.
- `demo/index.html`, `index.html` (landing page), `tools/stroke-recorder.html`:
  check for broken relative links/asset references, and that
  `tools/stroke-recorder-standalone.html`'s bundled data isn't stale relative
  to `js/src/glyph-data.json`/`stroke-data.json` (compare file mtimes/git log
  - it should be regenerated (`make build-recorder`) whenever those change).

## 8. Workflows (`.github/workflows/*.yml`)

- Do they still reference real Makefile targets (`grep -n "make " .github/workflows/*.yml`
  cross-checked against `make help`)?
- `release-on-merge.yml`/`publish.yml`/`pages.yml` - any hardcoded branch
  name, secret name, or path that drifted from current repo state (e.g. the
  default branch, checked via the actual repo settings, not assumed).
- `dependabot.yml` - are the ecosystems/paths it watches still accurate for
  the repo's current dependency files?

## 9. Docs freshness

- `README.md`/`CONTRIBUTING.md`/`docs/ARCHITECTURE.md`/`docs/ROADMAP.md`:
  do referenced file paths, function names, and counts (e.g. "~290
  hand-recorded atoms", "~2050 clusters") still match reality? Spot-check
  with `python3 tools/validate_data.py`'s printed counts.
- `docs/ROADMAP.md` - any item marked open that's actually already done
  (or vice versa)?
- Any `docs/*.md` no longer linked from anywhere (orphaned)?

## Report format

Order findings most-critical first. One entry per finding:

`[P0/P1/P2/P3] <category> - <one-line finding> — path/to/file:line`

Followed by one short paragraph: what's wrong, concrete evidence (the
command/grep that surfaced it, or the specific line), and why it matters.
Use:

- **P0** - broken/failing gate (CI red, data snapshot mismatch, demo
  actually broken).
- **P1** - real defect or drift that will cause a wrong render, a lost
  contribution, or mislead a contributor if untouched.
- **P2** - real but lower-impact (style/consistency drift, minor doc lag,
  a genuinely-dead but harmless export).
- **P3** - nice-to-have polish.

Group by section (1-9 above) under each priority, or by priority with
section noted inline - whichever reads clearer for the actual findings.
End with a short overall summary (health in one paragraph) and an explicit
note that prioritization is a starting point, not a mandate - the
maintainer decides what to fix now versus defer versus split out.

If a section has no findings, say so briefly rather than omitting it - "no
findings" is informative; silence reads as "not checked."
