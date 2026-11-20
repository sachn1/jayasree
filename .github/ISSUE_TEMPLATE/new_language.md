---
name: New language / script
about: Propose or start adding support for another script
title: "[lang] "
labels: new-language
---

<!--
See CONTRIBUTING.md ("Adding a new language") and docs/LANGUAGE_ONBOARDING_AGENTS.md for the
sequence: research, ghost font, atom set, then a native writer records the strokes, then process
and verify. The core is script-agnostic on purpose: a new language must not touch Malayalam's
code, tests or data. This template is just to coordinate who is doing what.
-->

**Script / language**

<!-- e.g. Tamil. Malayalam and Hindi are done; Tamil, Telugu, Kannada, Bengali and Sanskrit are planned. -->

**Are you a native speaker/writer of this script?**

<!--
Strokes drawn by someone who does not write the script daily are worse than no strokes at all (the
outline fallback is always correct, just not handwriting). If you cannot record strokes yourself,
say so - someone else may be able to record while you review authenticity, or this can sit as an
open request until a native writer picks it up.
-->

**Font**

<!--
An open-licensed font for the script, ideally one already used by that script's computing
community (Manjari for Malayalam, Noto Sans Devanagari for Hindi). It becomes the ghost outline.
-->

**What stage is this at?**

- [ ] Just proposing - looking for a native-speaker contributor to pick it up
- [ ] I am a native writer and want to record strokes myself
- [ ] Research or font selection is under way (`docs/languages/<code>/`)
- [ ] Already started - `_chars_<code>.py` / glyph data in progress
