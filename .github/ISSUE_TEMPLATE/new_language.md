---
name: New language / script
about: Propose or start adding support for a script other than Malayalam
title: "[lang] "
labels: new-language
---

<!--
See CONTRIBUTING.md's "Adding a new language" section for the full
step-by-step guide and ground rules (the core is script-agnostic on
purpose - a new script must not touch Malayalam's code, tests, or data).
This template is just to coordinate who's doing what before/while that
happens.
-->

**Script / language**

<!-- e.g. Tamil -->

**Are you a native speaker/writer of this script?**

<!--
CONTRIBUTING.md is explicit about this: strokes drawn by someone who
doesn't write the script daily are worse than no strokes at all (the
outline-trace fallback is always correct, just not real handwriting). If
you're proposing this but can't record strokes yourself, say so - someone
else may be able to record while you review authenticity, or this can sit
as an open request until a native writer picks it up.
-->

**Font**

<!--
An open-licensed font for this script, ideally one already used by that
script's computing community (the way Manjari is used here for
Malayalam) - this becomes the ghost outline source via
`tools/build_glyph_data.py`.
-->

**What stage is this at?**

- [ ] Just proposing - looking for a native-speaker contributor to pick it up
- [ ] I'm a native speaker and want to record strokes myself
- [ ] Already started - `_chars_<lang>.py` / glyph data in progress
