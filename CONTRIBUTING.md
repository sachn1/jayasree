# Contributing

Thanks for wanting to help! You can contribute **stroke data** (no coding), **code**, or a **new language**.

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems through
[SECURITY.md](SECURITY.md), not a public issue. Issues and PRs have templates; please use the one that fits.

## Quick start

```bash
make install     # poetry + npm dependencies
make test        # pytest + vitest
make lint        # ruff + interrogate + eslint + docstring check
make ci          # everything CI runs - green here means green there
make precommit   # every pre-commit hook, as CI runs them
```

Run `pre-commit install --hook-type commit-msg` once after cloning. Repo layout and the full command list
are in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Contributing stroke data (no code needed)

Open the [stroke recorder](tools/stroke-recorder.html) (or build an offline copy with
`make build-recorder`), trace the characters marked ○ (missing), export, and open a PR with the updated
`js/src/stroke-data.raw.json` (`stroke-data.<code>.raw.json` for other languages).

- **Only the recorder writes `stroke-data*.raw.json`.** Never hand-edit it.
- **Never edit `stroke-data*.json` or `glyph-data*.json`.** They are generated
  (`make process-strokes`, `make build-glyph-data`); regenerate, don't patch.
- **Whitespace and punctuation never get a recorded stroke.** They are plain text, handled outside the
  pipeline (`UNIVERSAL_CHARS` in `js/src/index.js`); the recorder refuses them and `tools/validate_data.py`
  fails CI if one appears in any data file.
- **Changing an already-recorded character is deliberate.** The snapshot test fails until you run
  `make update-snapshot` and commit the result in the same PR. New characters don't need this.
- **Licence:** stroke data for every language is CC BY-SA 4.0 ([LICENSE-DATA](LICENSE-DATA)). You are
  credited in git history; ask in the PR for more prominent credit. There is no private or premium tier.
  The engine code stays MIT.

## Contributing code

- **Tests are not optional.** New behaviour comes with tests; a bug fix comes with a regression test that
  fails before the fix. Keep coverage where it is or better (Python is about 95%).
- **Clean code is enforced.** `ruff`, `eslint`, `interrogate` and the docstring check gate every commit
  (pre-commit) and CI. If a linter and this document disagree, the linter wins.
- **Match the code around you** (comment density, naming, idiom). Comments explain *why*, not *what*.
- **Don't invent a parallel implementation** of something that exists; extend it (see
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).

## Docstrings

NumPy style with this project's split, enforced by `tools/check_docstrings.py` (in `make lint`):

| Kind | Docstring |
|---|---|
| Module, class, private function (leading `_`) | one line only; anything longer is a comment or belongs in `docs/` |
| Public function | one-line summary, then NumPy `Parameters` (if it takes arguments) and `Returns` (or `Yields`) |
| Test, nested helper, dunder | not checked (tests: one line, "Ensure that ...") |

A command-line tool's `--help` text lives in a `_HELP` constant, not in the docstring.

```python
def center(points: np.ndarray, field: DistField) -> np.ndarray:
    """Move each point onto the ink's ridge.

    Parameters
    ----------
    points : np.ndarray
        ``(n, 2)`` points in font units.
    field : DistField
        The glyph's distance field.

    Returns
    -------
    np.ndarray
        The centred points, same shape.
    """


def _snap(p: float) -> float:
    """Round `p` to the raster grid."""
```

## Commit messages & versioning

[Conventional commits](https://www.conventionalcommits.org/), enforced by commitizen (`cz commit` writes
one interactively). One line, no body unless it is a breaking change.

```
<type>(<scope>): <description>

feat(js): add per-play speed multiplier
fix(py): keep straight runs straight through loop-adjacent pieces
data(ml): record the remaining chillu letters
```

| Type | Use for |
|---|---|
| `feat` / `fix` | new behaviour / bug fix (these trigger a release) |
| `docs` `test` `refactor` `build` `ci` `chore` `perf` | everything else (no release) |

| Scope | Where the change lives |
|---|---|
| `js` / `py` | `js/src/` / `python/` |
| `data` | committed JSON; suffix the language, e.g. `data(ml)` |
| `tools` `demo` `docs` `ci` | the directory of that name |

Group commits by logical unit, not by file. Never edit a version number by hand: merging to `master`
bumps it from the commit history. How releases work: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md#releases).

## Pull requests

- Branch from `master` as `feature/<short-description>`; never commit to `master` directly.
- Keep each PR small and on one topic. Fill in the PR template's checklist.
- `make ci` must be green before you ask for review (the site deploys on merge to `master`).
- Data files under `js/src/` are always owner-reviewed (`.github/CODEOWNERS`).

## Adding a new language

Follow the pipeline in [`docs/LANGUAGE_ONBOARDING_AGENTS.md`](docs/LANGUAGE_ONBOARDING_AGENTS.md), or run
`/onboard-language <name>` in Claude Code, which detects the stage and enforces the sign-offs. One language
at a time:

1. **Research and profile** (`language-researcher`, `language-reviewer`); a human who reads the script signs off.
2. **Ghost font** (`font-selector`); a human signs off on one OFL-licensed, HarfBuzz-verified font.
3. **Atom set** (`atom-reducer`): `_chars_<code>.py`, the registry entry, `glyph-data.<code>.json`, the worklist.
4. **Record**: a native writer traces the worklist in the recorder. No agent does this.
5. **Process and verify**: `process_strokes.py --lang <name>`, `validate_data.py` and
   `node tools/coverage_report.js` until 100% with 0 fallbacks.
7. **Wire up** (`language-publisher`): demo tab, wordmark, README, site, docs. Then the owner looks (stage 6).
8. **Freeze** (the owner's call), see below.

Rules:

- **A new language must not touch a shipped one.** Today that is Malayalam and Hindi: no edits to their
  `_chars*.py`, `stroke-data*.raw.json` or `test_chars_*.py`. If shared code must change, every shipped
  language's tests must pass *unmodified*; if you had to change them, the feature wasn't common.
- Add `_chars_<code>.py` (`_chars_hi.py` is the worked example), a `LanguageSpec` in `languages.py`'s
  `LANGUAGES`, its own data files, and a `test_chars_<code>.py`.
- Recording needs a native writer; strokes from someone who doesn't write the script daily are worse than
  none (the outline fallback is always correct).
- Give it a wordmark: `tools/export_wordmark.py --lang <name> --output demo/jayasree.<code>.svg`, in a colour
  no other language uses (Hindi is red), kept in step with `--ms-ink-color` in `demo/demo.css`, the landing
  page and the README header.
- Hard stops: never skip a human sign-off, never run two languages at once, never hand-edit generated data.

## Language freezes

A language the owner has signed off is **frozen**: shared code may change, its output may not. Each has a
JS test, a Python test, a golden file and a raw-data snapshot, all run by `make ci`. How each works is in
the header of its test file.

| Language | JS test | Python test | Golden |
|---|---|---|---|
| Malayalam | `tests/malayalam-freeze.test.js` | `python/tests/test_malayalam_freeze.py` | `tests/freeze/malayalam-golden.json` |
| Hindi | `tests/hindi-freeze.test.js` | `python/tests/test_hindi_freeze.py` | `tests/freeze/hindi-golden.json` |

- **Never edit a golden, a snapshot or a frozen language's data to make a freeze test pass.**
- To change a frozen language on purpose: own PR, the owner's sign-off, then regenerate its golden
  (`tests/freeze/generate-<language>-golden.mjs`, labelled `approved change: <reason>`) and, for recorded
  strokes, `python3 tools/validate_data.py --update-snapshot --lang <code>`.
- To freeze a new language (the owner's call): copy Hindi's four freeze files and the snapshot, change the
  language, words, data files and label, and add a row above.
- Gate new behaviour on data a language opts into, never on a default a frozen language inherits.
- **What it does not cover:** the DOM and animation code (stroke order, timing, pen speed), the demo pages,
  the wordmark and the npm package contents. Check the demo by hand before a release.

## Data integrity & governance

Layers that keep the data trustworthy:

1. **Structural validation**: `tools/validate_data.py` (pre-commit and CI) rejects malformed data.
2. **Content snapshot**: per-cluster hashes in `python/tests/snapshots/` fail the tests if recorded data
   is lost or silently altered; re-approval is a visible diff.
3. **Generated vs. source**: `stroke-data*.raw.json` is the only hand-made file; the rest regenerates.
4. **Review and history**: everything lands by PR; git history records who contributed which strokes.
5. **Read-only runtime**: the site only fetches data; the recorder runs client-side and produces a file
   you submit through a PR.

If you find a way to corrupt the data past all of this, that's a bug; please open an issue.
