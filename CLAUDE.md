# CLAUDE.md

Operating notes for an AI agent working in this repo. This is a map and a
rulebook, not a tutorial - it points at the doc that actually explains each
thing rather than repeating it, because a second copy is a second place for
these facts to go stale. Read the target doc before touching the area it
covers.

## What this repo is

Jayasree animates Malayalam and Hindi (more Indic scripts planned) as handwriting -
stroke by stroke, not just a static glyph. A committed, hand-traced
`stroke-data.raw.json` is the actual content of the project; everything else
(`glyph-data.json`, `stroke-data.json`) is generated from it plus a font.
Read **`README.md`** first for what the project does and the 4-step
from-scratch workflow (generate ghost outlines → record strokes → process →
animate).

## Where to look for what

| Question | Doc |
|---|---|
| How do I use this / record strokes / run it | `README.md` |
| How does the pipeline work internally, file by file | `docs/ARCHITECTURE.md` |
| Why does centering/smoothing/straightening (or Hindi's cleanup) work this way | `docs/CENTERING_EXPERIMENTS.md`, `docs/HINDI_CLEANUP_EXPERIMENTS.md`, `docs/MALAYALAM_CLEANUP_EXPERIMENTS.md` |
| What's planned but not done | `docs/ROADMAP.md` |
| Rules for contributing code or stroke data, commit conventions | `CONTRIBUTING.md` |
| Onboarding a new Indic language: the agent sequence, gates, and Hindi's lessons | `docs/LANGUAGE_ONBOARDING_AGENTS.md` (or just `/onboard-language <name>`) |
| Invokable subagents - the onboarding pipeline's five (`language-researcher`, `language-reviewer`, `font-selector`, `atom-reducer`, `language-publisher`) and general-purpose ones (`code-reviewer`) | `.claude/agents/` |
| A whole-repo health check (not a diff review) | `/repo-audit` (`.claude/skills/repo-audit/`) |

`docs/ARCHITECTURE.md` in particular documents four real, shipped-and-fixed
composition bugs (anchor correction, segmentation priority, tighten-trim on
mark shifts, multi-glyph-base composition) as worked examples. Skim its
"Composition" section before changing anything in `index.js`'s
`composeMark`/`applyMarkStroke`/`tryComposeStroke` or
`stroke_compose.py` - each bug is exactly the kind of thing that's easy to
reintroduce by "obvious" refactoring.

## Hard rules (things that break CI or corrupt data if ignored)

- **Never hand-edit `js/src/stroke-data.raw.json`.** It's the project's only
  hand-authored source of truth, written exclusively by
  `tools/stroke-recorder.html`. Never hand-edit `glyph-data.json` or
  `stroke-data.json` either - both are generated (`make build-glyph-data`,
  `make process-strokes`). Regenerate, don't patch.
- **Changing an already-recorded cluster requires `make update-snapshot`**
  in the same commit/PR - `python/tests/test_data_snapshot.py` fails
  otherwise, by design. New clusters don't need this.
- **A shipped language's output is frozen** (today Malayalam and Hindi). `tests/<language>-freeze.test.js` and
  `python/tests/test_<language>_freeze.py` pin what its visitors see; shared code may change,
  a frozen language's letters/data may not. Never edit `tests/freeze/<language>-golden.json` or a frozen
  language's data to make them pass - see `CONTRIBUTING.md`'s "Language freezes".
- **A new language must not touch a shipped one.** Once a language is frozen (today:
  Malayalam - `python/src/jayasree/_chars.py`, `js/src/stroke-data.raw.json`,
  `python/tests/test_chars_malayalam.py` and its freeze golden - and Hindi, with the same files
  suffixed `.hi`/`_hi`), nothing a later change
  does may alter its letters, data or behaviour. If a change to shared/script-agnostic
  code is genuinely needed, every frozen language's tests must still pass
  unmodified - see `CONTRIBUTING.md`'s "Adding a new language". Freezing a language is the
  last step of onboarding it (`docs/LANGUAGE_ONBOARDING_AGENTS.md`, stage 8), the owner's call.
- **Whitespace/punctuation never gets a recorded stroke.** They're handled
  entirely outside the script pipeline (`UNIVERSAL_CHARS` in `index.js`);
  `tools/validate_data.py` fails CI if one ever appears as a cluster key.
- **Docstring split** (enforced by `tools/check_docstrings.py` in `make lint`): a module, a class and a
  private function (leading underscore) get a **one-line** docstring only; a public function gets a one-line
  summary plus NumPy `Parameters` and `Returns` sections, even when obvious. Details and an example
  in `CONTRIBUTING.md`'s "Docstrings". Check it before calling Python code done.
- **Commit messages are conventional-commits, enforced by commitizen** (a
  `commit-msg` hook rejects anything else). Version numbers are derived from
  commit history by `make bump` - never hand-edit a version number anywhere
  (`python/pyproject.toml`, `js/package.json`, `index.html`'s badge, etc.).
- **Don't invent a parallel implementation of something that already
  exists.** This project has already been through an exploratory phase that
  left behind duplicate scratch tooling (a reduced-glyph-data extractor and a
  flat stroke composer that reimplemented, less correctly, what
  `build_glyph_data.py`'s `marks` table and `process_strokes.py --expand`
  already do) - those were removed. If a task looks like "reduce the atom
  set" or "compose strokes from parts," the real mechanism is the `marks`
  table + `tryComposeStroke`/`stroke_compose.py`, documented in
  `docs/ARCHITECTURE.md`'s "Composition" section - extend that, don't
  reinvent it beside it.

## Common commands

```bash
make install         # poetry (python/) + npm ci (repo root)
make lint             # ruff + interrogate + eslint
make test              # pytest (+coverage) + vitest (+coverage)
make validate-data      # structural check of every language's committed JSON data files
make ci                  # everything CI runs, both languages, in one shot
make build-glyph-data FONT=/path/to/Font.ttf   # regenerate glyph-data.json
make process-strokes                            # regenerate stroke-data.json
make coverage-report                             # direct/composed/fallback per cluster
make demo                                        # serve demo + stroke recorder at :8000
```

`--lang`/`PROJECT_LANG=` take the registry name (`hindi`), not the code
(`hi`) - the code is for file suffixes and commit scopes. The Python tools
need their dependencies (`uharfbuzz`): run them via `cd python && poetry run
python ../tools/<tool>.py ...` if a bare `python3` fails to import them.

`make ci` is exactly what CI runs (`.github/workflows/ci.yml` just calls
`make ci-py`/`make ci-js`) - if it's green locally, trust that it's green in
CI. Run it before calling any code change done.

## Git workflow

Full rationale (versioning, release automation) is in `CONTRIBUTING.md`'s
"Commit messages & versioning" - this section is the quick-reference so an
agent doesn't have to re-derive it each time.

- **Branches**: `feature/<short-description>` for anything non-trivial
  (`feature/language-onboarding-phase0` is the precedent). Don't work
  directly on `master`.
- **Commits are conventional commits**, enforced by a commitizen
  `commit-msg` hook - anything else is rejected:

  ```
  <type>(<scope>): <one-line description>
  ```

  **Single line only, unless it's a breaking change** - a `BREAKING CHANGE:`
  footer is what's allowed to add a body. And a breaking change is never a
  unilateral call: **discuss it with the user before committing** - it
  forces a major version bump (`make bump`'s semver logic) and everyone
  downstream of the npm package feels it, so confirm it's actually intended
  and get the footer's wording right together, rather than committing first
  and explaining after.

  Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`,
  `perf`. Scope is the directory the change lives in:

  | Scope | Directory |
  |---|---|
  | `js` | `js/src/` (the runtime library) |
  | `py` | `python/` (the Python package + its tests) |
  | `tools` | `tools/` (build/validate/authoring scripts) |
  | `data` | committed JSON data - suffix the language, e.g. `data(ml)` |
  | `demo` / `docs` / `ci` | the corresponding directory |

- **Group commits by logical unit, not by file-save order.** Each commit
  should stand on its own (ideally passing `make ci` at that point) - e.g.
  a registry module + the tests that exercise it in one commit, a
  Makefile wiring change as its own `build` commit once the tools it
  wires already exist. Squashing an entire multi-file change into one
  commit, or committing every file individually regardless of how they
  relate, are both wrong here.
- **Never hand-edit a version number** - `feat`/`fix`/a `BREAKING CHANGE`
  footer drive `make bump`'s semver choice automatically (minor/patch/major
  respectively); a docs/chore/ci/non-breaking-refactor-only set of commits
  triggers no release at all. See "Hard rules" above.
- Don't push or open a PR unless asked - committing locally on a feature
  branch doesn't imply either.

## Current scope

Two languages have data, both frozen: **Malayalam** (`_chars.py`, `glyph-data.json`, `stroke-data(.raw).json`,
unsuffixed) and **Hindi** (`_chars_hi.py`, `glyph-data.hi.json`, `stroke-data.hi(.raw).json`; 183 recorded atoms,
100% cluster coverage). `python/src/jayasree/languages.py`'s `LANGUAGES` registry maps a language name to its
character module and data paths (unsuffixed for Malayalam, `.{code}` for the rest); the build, process and CLI
tools all take `--lang` / `PROJECT_LANG=`. `validate_data.py` auto-discovers every language's files and stays
stdlib-only on purpose (the pre-commit hook runs it with bare `python3`).

Onboarding a language is research (`language-researcher` + `language-reviewer`) → sign-off → font
(`font-selector`) → sign-off → atom set (`atom-reducer`) → a human records → process and verify → wire up
(`language-publisher`) → the owner freezes it. `/onboard-language <name>` runs it and enforces the gates;
**never invoke Agent 2/3 without a real sign-off from the user in the conversation**. The spec, the roster still
to do and the caution against generalizing from Malayalam are in `docs/LANGUAGE_ONBOARDING_AGENTS.md`.
