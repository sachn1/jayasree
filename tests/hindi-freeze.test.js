/**
 * Hindi freeze: nothing a Hindi visitor sees may change.
 *
 * Compares the working tree against `tests/freeze/hindi-golden.json`, a snapshot taken when the owner signed
 * Hindi off - see `tests/freeze/hindi-snapshot.mjs` for what it covers and, in CONTRIBUTING.md's "Language
 * freezes", what it does not. Shared code may change; Hindi's letters, data and behaviour may not. A failure
 * names the clusters, words or files that moved.
 *
 * If Hindi is *supposed* to change, regenerate the golden file in that same PR (instructions in
 * `tests/freeze/generate-hindi-golden.mjs`) so the change is explicit and reviewed.
 *
 * Run just this file: `npx vitest run tests/hindi-freeze.test.js`.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { snapshot, STAGES } from "./freeze/hindi-snapshot.mjs";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const golden = JSON.parse(readFileSync(`${ROOT}tests/freeze/hindi-golden.json`, "utf-8"));

/** Keys whose value differs between two flat objects (including keys present in only one). */
const differing = (a, b) =>
  [...new Set([...Object.keys(a), ...Object.keys(b)])].filter((k) => a[k] !== b[k]).sort();

let now;
beforeAll(async () => {
  now = await snapshot(ROOT);
}, 120_000);

describe("Hindi freeze", () => {
  it("has a golden snapshot worth comparing against", () => {
    expect(Object.keys(golden.clusters).length).toBeGreaterThan(4000);
    expect(Object.keys(golden.words).length).toBeGreaterThan(30);
    // Taken at the owner's sign-off, or regenerated for an explained, approved change - never unlabelled.
    expect(golden.source).toMatch(/^(owner sign-off: .+|approved change: .+)/);
  });

  it("exercises every composition step the runtime has", () => {
    // A step that is renamed or removed must not vanish from the comparison unnoticed.
    expect(now.stages).toEqual(STAGES);
  });

  it("leaves Hindi's data files untouched, and adds no field to its glyph data", () => {
    expect(differing(golden.data, now.data)).toEqual([]);
  });

  it("draws every Hindi cluster exactly as it was signed off (ghost outline and strokes)", () => {
    expect(differing(golden.clusters, now.clusters)).toEqual([]);
  });

  it("segments and draws real Hindi words exactly as it was signed off", () => {
    expect(differing(golden.words, now.words)).toEqual([]);
  });
});
