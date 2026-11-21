<!--
Thanks for the PR! CONTRIBUTING.md has the full rules; this is the short checklist so review goes
smoothly. Delete lines that do not apply.
-->

## What this changes and why

## Checklist

- [ ] `make ci` passes locally (it runs exactly what CI runs)
- [ ] New behavior has tests; a bug fix has a regression test that fails without the fix
- [ ] Docs are updated where they describe what changed (README, `docs/`, CONTRIBUTING, docstrings)
- [ ] **Every frozen language (Malayalam, Hindi) is unchanged**: the freeze tests pass *unmodified*
      (CONTRIBUTING, "The Malayalam freeze" and "The Hindi freeze"). If one is meant to change, say so
      here, get the owner's sign-off, and regenerate its golden in this PR
- [ ] Generated data (`glyph-data*.json`, `stroke-data*.json`) was regenerated with the tools
      (`make build-glyph-data`, `make process-strokes`), never hand-edited
- [ ] Recorded strokes (`stroke-data*.raw.json`) come from `tools/stroke-recorder.html`, drawn by a
      native writer of the script; if an *already-recorded* cluster changed, `make update-snapshot`
      was run and is included
- [ ] Commit messages are one-line [Conventional Commits](https://www.conventionalcommits.org/)
      (enforced by the `commit-msg` hook)
- [ ] The branch is up to date with its base and nothing private (keys, emails) is committed
