/**
 * Regenerate `hindi-golden.json` from a tree of Hindi's code and data.
 *
 * Only run this when Hindi is *meant* to change - in the PR that changes it, with the owner's sign-off.
 * The baseline was taken from `feature/hindi-onboarding` when the owner said "Hindi ships":
 *
 *   node tests/freeze/generate-hindi-golden.mjs . tests/freeze/hindi-golden.json \
 *     "owner sign-off: Hindi ships (<branch>@<short sha>)"
 *
 * After an approved Hindi change, regenerate from the *changed* working tree, in the same PR, labelled:
 *
 *   node tests/freeze/generate-hindi-golden.mjs . tests/freeze/hindi-golden.json \
 *     "approved change: <what and why> (<PR or commit>)"
 *
 * The label must read `owner sign-off: ...` or `approved change: ...`; the test rejects anything else.
 *
 * Usage: node generate-hindi-golden.mjs <root> <out.json> <label>
 */

import { writeFileSync } from "node:fs";
import { snapshot } from "./hindi-snapshot.mjs";

const [root, out, label] = process.argv.slice(2);
if (!root || !out || !label) {
  console.error("usage: node generate-hindi-golden.mjs <root> <out.json> <label>");
  process.exit(2);
}
const taken = await snapshot(root);
writeFileSync(out, `${JSON.stringify({ source: label, ...taken }, null, 1)}\n`);
console.log(
  `${out}: ${Object.keys(taken.clusters).length} clusters, ${Object.keys(taken.words).length} words, ` +
    `${Object.keys(taken.data).length} data hashes (from ${label})`
);
