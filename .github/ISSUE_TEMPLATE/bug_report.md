---
name: Bug report
about: A letter, word, or animation renders incorrectly
title: "[bug] "
labels: bug
---

<!--
Before filing: try the word at https://sachn1.github.io/jayasree/ first, if
you haven't already - it's the fastest way to confirm what's actually
happening and to get the console warning mentioned in step 3 below.
-->

**Word or character typed**

<!-- Paste the exact text, e.g. നിൻറെ -->

**Expected vs. actual**

<!--
What should it look like vs. what actually rendered? A screenshot or
screen recording of the demo is the most useful thing you can attach here.
-->

**Which part is wrong?**

<!--
This narrows down where the bug likely lives, so please check one:
- [ ] The faint background letterform (the "ghost") is already the wrong
      shape - the bug is probably in the underlying glyph data.
- [ ] The ghost looks right, but the animated pen stroke is wrong, missing,
      or in the wrong position - the bug is probably in the stroke/composition
      logic.
- [ ] Not sure / both look wrong.
-->

**Browser console output**

<!--
Open your browser's dev tools console before/while typing the word. If you
see a line like `jayasree: no glyph data for "..." in "..." - skipping`,
paste it here - it names the exact missing piece.
-->

**Environment**

- Browser:
- OS:
- Where you saw this: [demo site / npm package / other]
