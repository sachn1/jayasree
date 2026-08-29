<!--
Thanks for the PR! A couple of things CONTRIBUTING.md asks for, so review
goes smoothly:
-->

**What this changes and why**

**Checklist**

- [ ] `make ci` passes locally (runs exactly what CI runs)
- [ ] New behavior has tests; bug fixes have a regression test that fails without the fix
- [ ] If this changes `js/src/stroke-data.raw.json` for an *already-recorded* cluster (not a new one), `make update-snapshot` was run and the updated snapshot is included in this PR
- [ ] If this is stroke data: it was recorded by a native speaker/writer of the script (see CONTRIBUTING.md)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced by the `commit-msg` hook)
