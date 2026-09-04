.PHONY: help install install-py install-js \
	lint lint-py lint-js format format-py \
	test test-py test-js \
	validate-data precommit \
	ci ci-py ci-js \
	demo record build-glyph-data process-strokes build-recorder update-snapshot \
	coverage-report \
	bump bump-ci clean

# Single source of truth for the commands used both by contributors locally
# and by .github/workflows/ci.yml - the workflow calls `make ci-py`/`make
# ci-js` rather than duplicating these commands, so there's exactly one place
# that defines "lint" or "test" for this repo.

help:
	@echo "jayasree - common commands"
	@echo ""
	@echo "  make install        install both Python (poetry) and JS (npm) dependencies"
	@echo "  make lint           lint Python + JS"
	@echo "  make format         auto-fix formatting (Python only - see lint-js for JS)"
	@echo "  make test           run Python + JS test suites"
	@echo "  make validate-data  structural validation of the 3 committed JSON data files"
	@echo "  make precommit      run every pre-commit hook against all files"
	@echo "  make ci             everything CI runs, for both languages, in one shot"
	@echo "  make demo           serve the demo AND the stroke recorder (same server, see"
	@echo "                      its printed URLs) at :8000 - alias: make record"
	@echo "  make build-glyph-data [FONT=/path/to/Font.ttf] [LANG=malayalam]   regenerate glyph-data.json"
	@echo "  make process-strokes [LANG=malayalam]              regenerate stroke-data.json"
	@echo "  make build-recorder                                bundle the standalone recorder"
	@echo "  make update-snapshot [LANG=malayalam]              re-approve the data snapshot"
	@echo "  make validate-data [LANG=malayalam]                (LANG only affects --update-snapshot)"
	@echo "  make coverage-report                               per-cluster direct/composed/fallback report"
	@echo ""
	@echo "  LANG picks a registry key from python/src/jayasree/languages.py -"
	@echo "  see docs/LANGUAGE_ONBOARDING_AGENTS.md. Defaults to malayalam everywhere."
	@echo "  make bump           cut a release: bump semver from commit history, tag, changelog"
	@echo "  make clean          remove venvs/node_modules/coverage artifacts"

# ── Install ──────────────────────────────────────────────────────────────

install: install-py install-js

install-py:
	cd python && poetry install

install-js:
	npm ci

# ── Lint / format ────────────────────────────────────────────────────────

lint: lint-py lint-js

lint-py:
	cd python && poetry run ruff check .. && poetry run ruff format --check ..
	cd python && poetry run interrogate --fail-under=90 --ignore-init-module --ignore-magic src ../tools

lint-js:
	npm run lint

format: format-py

format-py:
	cd python && poetry run ruff format ..

# ── Test ─────────────────────────────────────────────────────────────────

test: test-py test-js

test-py:
	cd python && poetry run pytest

test-js:
	npm test

# ── Data integrity ───────────────────────────────────────────────────────

validate-data:
	python3 tools/validate_data.py

update-snapshot:
	python3 tools/validate_data.py --update-snapshot $(if $(LANG),--lang $(LANG),)

# ── Release ──────────────────────────────────────────────────────────────

# Runs from the repo root on purpose: cz reads [tool.commitizen] from the
# root pyproject.toml and resolves every `version_files` entry relative to
# cwd. `poetry -C python run cz bump` silently broke this - contrary to the
# comment this used to have, `-C` *does* chdir into `python/` for the whole
# invocation (verified: `poetry -C python run pwd` prints .../python), so
# cz found the root config (it searches upward) and correctly bumped its
# own version + wrote CHANGELOG.md at the root, but then resolved
# version_files paths like "index.html" against python/index.html - which
# doesn't exist - and silently skipped every one of them. Shipped as v0.2.0
# with python/pyproject.toml, __init__.py, js/package.json, and index.html
# all still reading 0.1.0. Invoking the venv's cz binary directly instead of
# through `poetry run`/`poetry -C` sidesteps the chdir entirely.
bump:
	python/.venv/bin/cz bump

# Same as `bump`, but non-interactive (`--yes`) for the automated
# release-on-PR-merge workflow (.github/workflows/release-on-merge.yml) -
# see that target's comment above for why this still doesn't go through
# `poetry run`/`poetry -C`. Exits non-zero (21 if the merged commits don't
# include anything release-worthy, e.g. a docs-only PR; 3 if there are no
# new commits at all) when there's nothing to release - the caller decides
# whether that's a real failure or just a no-op.
bump-ci:
	python/.venv/bin/cz bump --yes

# ── Everything at once ───────────────────────────────────────────────────

precommit:
	cd python && poetry run pre-commit run --all-files

# ci-py / ci-js mirror the two parallel jobs in .github/workflows/ci.yml
# exactly - each is what that job's "run" steps reduce to after checkout
# and toolchain setup (which only make sense inside the runner, not here).
ci-py: install-py lint-py test-py validate-data

ci-js: install-js lint-js test-js

ci: ci-py ci-js

# ── App commands ─────────────────────────────────────────────────────────

# One server, two jobs: it serves the interactive demo (demo/demo_index.html)
# *and* the whole repo as static files, which is what makes the stroke
# recorder (tools/stroke-recorder.html) reachable through it too - serve.py
# prints both URLs on startup for exactly this reason. `record` is just a
# more discoverable name for anyone who only wants the recorder.
# Runs inside the poetry venv: serve.py imports jayasree (uharfbuzz)
# for its /api/shape endpoint, which a bare system python3 won't have.
demo record:
	cd python && poetry run python ../demo/serve.py

build-glyph-data:
	cd python && poetry run python ../tools/build_glyph_data.py $(FONT) $(if $(LANG),--lang $(LANG),)

process-strokes:
	python3 tools/process_strokes.py --preset=full $(if $(LANG),--lang $(LANG),)

build-recorder:
	python3 tools/build_standalone_recorder.py

coverage-report:
	node tools/coverage_report.js
	@echo ""
	@echo "For another language or a pre-recording (simulated) check, run directly:"
	@echo "  node tools/coverage_report.js --glyph-data js/src/glyph-data.<code>.json --stroke-data js/src/stroke-data.<code>.json"
	@echo "  node tools/coverage_report.js --simulate-atoms <file-of-planned-atoms> --glyph-data <path> [--verbose] [--min-coverage N]"

# ── Housekeeping ─────────────────────────────────────────────────────────

clean:
	rm -rf python/.venv node_modules python/.pytest_cache python/htmlcov .coverage
