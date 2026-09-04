# CLAUDE.md

Operating notes for an AI agent working in this repo. This is a map and a
rulebook, not a tutorial - it points at the doc that actually explains each
thing rather than repeating it, because a second copy is a second place for
these facts to go stale. Read the target doc before touching the area it
covers.

## What this repo is

Jayasree animates Malayalam (soon: other Indic scripts) as handwriting -
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
| Why does centering/smoothing/straightening work this way | `docs/CENTERING_EXPERIMENTS.md` |
| What's planned but not done | `docs/ROADMAP.md` |
| Rules for contributing code or stroke data, commit conventions | `CONTRIBUTING.md` |
| Plan for onboarding a new Indic language via agents | `docs/LANGUAGE_ONBOARDING_AGENTS.md` |
| Invokable subagents for that pipeline (`Agent(language-researcher, ...)` etc.) | `.claude/agents/` |

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
- **A new language must not touch Malayalam's files.** No edits to
  `python/src/jayasree/_chars.py`, `js/src/stroke-data.raw.json`, or
  `python/tests/test_chars_malayalam.py`. If a change to shared/script-agnostic
  code is genuinely needed, Malayalam's existing tests must still pass
  unmodified - see `CONTRIBUTING.md`'s "Adding a new language".
- **Whitespace/punctuation never gets a recorded stroke.** They're handled
  entirely outside the script pipeline (`UNIVERSAL_CHARS` in `index.js`);
  `tools/validate_data.py` fails CI if one ever appears as a cluster key.
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
make validate-data      # structural check of the 3 committed JSON data files
make ci                  # everything CI runs, both languages, in one shot
make build-glyph-data FONT=/path/to/Font.ttf   # regenerate glyph-data.json
make process-strokes                            # regenerate stroke-data.json
make demo                                        # serve demo + stroke recorder at :8000
```

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

Malayalam is the only language with actual data (`_chars.py`,
`glyph-data.json`, `stroke-data(.raw).json`) today, but the tooling is now
language-parametrized (Phase 0 of `docs/LANGUAGE_ONBOARDING_AGENTS.md`,
done): `python/src/jayasree/languages.py`'s `LANGUAGES` registry is the
single source of truth mapping a language name to its character-inventory
module and its data-file paths (unsuffixed for Malayalam, `.{code}`-suffixed
for anything else). `build_glyph_data.py`, `cli.py alphabet`, and
`process_strokes.py` all take `--lang`/`Makefile`'s `LANG=`; `validate_data.py`
auto-discovers whichever languages' files exist under `js/src/` (and stays
dependency-free/stdlib-only on purpose - see its module docstring - since
the pre-commit hook runs it with bare `python3`, no guaranteed `uharfbuzz`).

The target roster for onboarding an actual second language (Hindi, Tamil,
Telugu, Kannada, Bengali, Sanskrit, one at a time, more beyond that) and the
multi-agent pipeline for doing it (research → ghost font → reduced labeling
set) are in `docs/LANGUAGE_ONBOARDING_AGENTS.md` - including an explicit
caution against generalizing from Malayalam's Dravidian-specific quirks
(chillu, its particular conjunct/ligature set) when profiling a
structurally different script like Devanagari, Tamil, Telugu, Kannada, or
Bengali.
