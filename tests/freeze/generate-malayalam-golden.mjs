/**
 * Regenerate `malayalam-golden.json` from a tree of Malayalam's code and data.
 *
 * Only run this when Malayalam is *meant* to change - in the PR that changes it, with the owner's
 * sign-off - or to re-create the baseline from production.
 *
 * Baseline, from production (`origin/master`):
 *
 *   git fetch origin master
 *   TMP=$(mktemp -d)
 *   git archive origin/master js python/src/jayasree/_chars.py python/tests/test_chars_malayalam.py \
 *     python/tests/snapshots | tar -x -C "$TMP"
 *   node tests/freeze/generate-malayalam-golden.mjs "$TMP" tests/freeze/malayalam-golden.json \
 *     "origin/master@$(git rev-parse --short origin/master)"
 *
 * After an approved Malayalam change, regenerate from the *changed* working tree, in the same PR, and
 * label it with the reason so the history is readable:
 *
 *   node tests/freeze/generate-malayalam-golden.mjs . tests/freeze/malayalam-golden.json \
 *     "approved change: <what and why> (<PR or commit>)"
 *
 * The golden is not the whole freeze: `tests/malayalam-freeze.test.js` also pins, in code, the approved
 * extra glyph-data fields (content hashes, meta values) and the composition steps. An approved change to
 * any of those needs its pin updated in the same PR - do not loosen the test instead.
 *
 * The label is required and must read `origin/master@<sha>` or `approved change: <reason>`; the test
 * rejects anything else.
 *
 * Usage: node generate-malayalam-golden.mjs <root> <out.json> <label>
 */

import { writeFileSync } from "node:fs";
import { snapshot } from "./malayalam-snapshot.mjs";

const [root, out, label] = process.argv.slice(2);
if (!root || !out || !label) {
  console.error("usage: node generate-malayalam-golden.mjs <root> <out.json> <label>");
  process.exit(2);
}
const taken = await snapshot(root);
writeFileSync(out, `${JSON.stringify({ source: label, ...taken }, null, 1)}\n`);
console.log(
  `${out}: ${Object.keys(taken.clusters).length} clusters, ${Object.keys(taken.words).length} words, ` +
    `${Object.keys(taken.data).length} data hashes (from ${label})`
);
