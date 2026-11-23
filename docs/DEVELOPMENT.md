# Development

Repo layout, the `make` commands CI runs, deployment, and known limitations. Contributor rules (commit
messages, the Malayalam and Hindi freezes, how to add a language) are in [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Repo layout

```
jayasree/
├── js/
│   ├── src/index.js               # main export - segmentation, composition, animation
│   ├── src/glyph-data.json        # pre-computed font outlines + marks table (commit)
│   ├── src/stroke-data.raw.json   # hand-authored strokes, source of truth (commit)
│   ├── src/stroke-data.json       # processed, ready-to-load (commit - generated)
│   └── src/*.hi.json              # Hindi's three files: glyph-data.hi / stroke-data.hi.raw / stroke-data.hi
├── python/                        # build-time shaper + stroke-processing library (Poetry project)
│   ├── src/jayasree/
│   │   ├── cli.py                 # `shape`/`alphabet` CLI (see python/README.md)
│   │   ├── languages.py           # LANGUAGES registry: name -> chars module + data paths
│   │   ├── _chars.py / _chars_hi.py   # per-language character inventories (Malayalam / Hindi)
│   │   ├── strokes.py             # HarfBuzz shaping
│   │   ├── geometry.py            # corner-aware smoothing
│   │   ├── centering.py           # gradient-ascent centering
│   │   ├── ghost_reference.py     # ghost-outline-guided straightening
│   │   └── stroke_compose.py      # multi-glyph + mark stroke composition
│   └── tests/snapshots/           # committed data-integrity snapshot (see CONTRIBUTING.md "Data integrity & governance")
├── tools/
│   ├── build_glyph_data.py            # generates js/src/glyph-data.json
│   ├── process_strokes.py             # generates js/src/stroke-data.json
│   ├── validate_data.py               # structural validation + content-snapshot tooling
│   ├── coverage_report.js             # per-cluster direct/composed/fallback report (real or simulated)
│   ├── stroke-recorder.html/.css/.js  # browser tool for authoring stroke-data.raw.json
│   └── build_standalone_recorder.py   # bundles the recorder into one offline file
├── demo/
│   ├── index.html / demo.js / demo.css   # the demo: one page, a tab per language (LANGUAGES table in demo.js)
│   ├── logo-preview.html          # standalone preview of the animated wordmark
│   └── serve.py
├── docs/
│   ├── ARCHITECTURE.md            # canonical pipeline + composition reference
│   ├── CENTERING_EXPERIMENTS.md   # centering/smoothing/straightening experiments log
│   ├── HINDI_CLEANUP_EXPERIMENTS.md   # what was tried for Hindi's stroke cleanup
│   ├── LANGUAGE_ONBOARDING_AGENTS.md   # the multi-agent onboarding pipeline (spec + lessons)
│   ├── languages/<code>/          # per-language profile, font report, worklist (ml, hi)
│   ├── centering-example/         # before/after SVGs referenced from those docs
│   └── ROADMAP.md                 # planned/not-yet-done work
├── tests/index.test.js             # vitest - index.js's composition/segmentation engine
├── index.html                      # landing page (GitHub Pages site root)
├── .github/workflows/ci.yml        # thin wrapper around `make ci-py` / `make ci-js`
├── .github/workflows/pages.yml     # deploys landing page + demo + recorder to GitHub Pages
├── Makefile                        # single source of truth for local + CI commands
├── pyproject.toml                  # ruff config only (repo root - see file header for why)
├── eslint.config.js / vitest.config.js / package.json   # repo-level JS dev tooling
├── CONTRIBUTING.md                 # ground rules: code, tests, data integrity, new languages
├── CLAUDE.md                       # operating notes + hard rules for an AI agent in this repo
├── .claude/agents/                 # the onboarding pipeline's agents + a code reviewer
├── .claude/skills/onboard-language/   # /onboard-language - runs the agents in order
├── LICENSE / LICENSE-DATA          # MIT (code) / CC BY-SA 4.0 (stroke data + artwork)
└── README.md
```

## Development

A `Makefile` at the repo root is the single source of truth for the
commands below - `.github/workflows/ci.yml` calls `make ci-py`/`make ci-js`
rather than duplicating them, so local and CI behavior can't drift apart.
Run `make help` for the full list.

```bash
make install       # poetry install (python/) + npm ci (repo root)
make lint           # ruff (lint + format check) + interrogate + eslint
make test           # pytest (+ coverage) + vitest (+ coverage)
make validate-data   # structural check of every language's committed JSON data files
make coverage-report # per-cluster direct/composed/fallback report (Malayalam by default;
                     #   see its output for the Hindi invocation)
make precommit       # every pre-commit hook against all files
make ci              # everything CI runs, both languages, in one shot
```

Individual pieces are also available split by language (`make lint-py`,
`make lint-js`, `make test-py`, `make test-js`, ...) or as `make ci-py`/
`make ci-js` - exactly what each CI job runs.

Both linters also run automatically via `pre-commit` (`.pre-commit-config.yaml`).
DOM-dependent parts of `index.js` (the actual SVG animation) aren't covered
by the JS unit tests - they need real browser SVG geometry APIs that jsdom
doesn't implement; verify those with the demo (`make demo`) or a
Playwright-driven check instead.

## Deployment

The live site is deployed from this repo by `.github/workflows/pages.yml` on every push to
`master` (one-time setup: repo Settings -> Pages -> Source: *GitHub Actions*). It does not wait for
CI, so a PR must be green before it is merged.

## Releases

Versions come from commit history (`feat` minor, `fix` patch, a `!` breaking commit or `BREAKING CHANGE` footer on
a `feat`/`fix` major); never edit one by hand. Merging to `master` runs `release-on-merge.yml`, which bumps, tags
and updates the changelog only if the merge has a `feat`, `fix`, `refactor`, `perf` or breaking commit (what the
changelog lists, so no release has an empty entry). `publish.yml` publishes to npm only if `js/src/`
changed since the previous tag, and only while the repository variable `NPM_PUBLISH_ENABLED` is `true`
(held for now: setting it does not publish a tag already pushed, so run `publish.yml` by hand
(`workflow_dispatch`) to publish the held release). The workflows document the details.

## Status and known limitations

Early. Two languages have data:

- **Malayalam** - ~300 atoms hand-authored; composition (see
  [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)) extends them to the ~2050
  clusters `glyph-data.json` covers.
- **Hindi** - all 183 atoms of its reduced worklist are recorded; they cover
  all 2443 clusters in `glyph-data.hi.json` with no outline fallbacks. The
  strokes are also cleaned against the font's own geometry
  (`jayasree.cleanup`, see "Cleanup (Hindi)" in [`ARCHITECTURE.md`](ARCHITECTURE.md)),
  which is Hindi-only.

`glyph-data.json` pre-shapes every consonant+vowel-sign and conjunct combination HarfBuzz can produce. Pruning
that, and the rest of the open work, is in [`ROADMAP.md`](ROADMAP.md).
