/**
 * Malayalam freeze: nothing a Malayalam visitor sees may change.
 *
 * Compares the working tree against `tests/freeze/malayalam-golden.json`, a snapshot taken from production
 * (`origin/master`) - see `tests/freeze/malayalam-snapshot.mjs` for what it covers and, in
 * CONTRIBUTING.md's "The Malayalam freeze", what it does not. Shared code may change; Malayalam's letters,
 * data and behaviour may not. A failure names the clusters, words or files that moved.
 *
 * If Malayalam is *supposed* to change, regenerate the golden file in that same PR (instructions in
 * `tests/freeze/generate-malayalam-golden.mjs`) so the change is explicit and reviewed.
 *
 * Run just this file: `npx vitest run tests/malayalam-freeze.test.js`.
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { canonical, snapshot } from "./freeze/malayalam-snapshot.mjs";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const golden = JSON.parse(readFileSync(`${ROOT}tests/freeze/malayalam-golden.json`, "utf-8"));
const glyphData = JSON.parse(readFileSync(`${ROOT}js/src/glyph-data.json`, "utf-8"));

/** Short content hash of a value, independent of key order. */
const contentHash = (value) => createHash("sha256").update(canonical(value)).digest("hex").slice(0, 16);

/**
 * Fields Malayalam's glyph data may have beyond `clusters`/`marks`/`meta{unitsPerEm,ascent,descent}`.
 * Production has none of them; they arrive with the data-driven refactor (the runtime reads these tables from
 * data instead of constants) and the recorder's per-language text. Each is *allowed but not required* so this
 * test passes on production and after that refactor, and is pinned by content when present. Any other field,
 * or an edit to one of these, is a change to Malayalam's data and must fail here.
 */
const APPROVED_EXTRA_GLYPH_DATA = {
  topLevel: ["legacyEncodings", "splitVowelParts"],
  contentHashes: { legacyEncodings: "fbe073ae5ddbafe7", splitVowelParts: "7ee946ea7fd0e63c" },
  // meta: required values, then values an approved extra must have when present
  metaRequired: { unitsPerEm: 2048, ascent: 1500, descent: -750 },
  metaApproved: { projectNameNative: "ജയശ്രീ", exampleCustomCluster: "ന്ന" },
};

/** Keys whose value differs between two flat objects (including keys present in only one). */
const differing = (a, b) =>
  [...new Set([...Object.keys(a), ...Object.keys(b)])].filter((k) => a[k] !== b[k]).sort();

let now;
beforeAll(async () => {
  now = await snapshot(ROOT);
}, 120_000);

describe("Malayalam freeze", () => {
  it("has a golden snapshot worth comparing against", () => {
    expect(Object.keys(golden.clusters).length).toBeGreaterThan(2000);
    expect(Object.keys(golden.words).length).toBeGreaterThan(30);
    // Production's own snapshot, or one regenerated for an explained, approved change - never unlabelled.
    expect(golden.source).toMatch(/^(origin\/master@[0-9a-f]+|approved change: .+)/);
  });

  it("exercises every composition step the runtime has", () => {
    // The snapshot skips a step the runtime lacks (production has no contextual-form step). A step that is
    // renamed or removed must not vanish from the comparison unnoticed, so the runtime must match one of the
    // two known shapes exactly.
    expect([
      ["tryComposeStroke", "tryComposeFromCharacters"],
      ["tryComposeStroke", "tryComposeContextualForm", "tryComposeFromCharacters"],
    ]).toContainEqual(now.stages);
  });

  it("leaves Malayalam's data files untouched", () => {
    expect(differing(golden.data, now.data)).toEqual([]);
  });

  it("adds no field to Malayalam's glyph data beyond the approved ones", () => {
    const unexpected = (keys, required, allowed) => keys.filter((k) => !required.includes(k) && !allowed.includes(k));
    expect(
      unexpected(Object.keys(glyphData), ["clusters", "marks", "meta"], APPROVED_EXTRA_GLYPH_DATA.topLevel)
    ).toEqual([]);
    const { metaRequired, metaApproved } = APPROVED_EXTRA_GLYPH_DATA;
    expect(unexpected(Object.keys(glyphData.meta), Object.keys(metaRequired), Object.keys(metaApproved))).toEqual([]);
    for (const [k, v] of Object.entries(metaRequired)) expect(glyphData.meta[k], `meta.${k}`).toBe(v);
    for (const [k, v] of Object.entries(metaApproved)) if (k in glyphData.meta) expect(glyphData.meta[k]).toBe(v);
    // Required fields stay required, and an approved extra, when present, must have exactly its approved content.
    for (const key of ["clusters", "marks", "meta"]) expect(glyphData, key).toHaveProperty(key);
    for (const [field, hash] of Object.entries(APPROVED_EXTRA_GLYPH_DATA.contentHashes)) {
      if (field in glyphData) expect(contentHash(glyphData[field]), `${field} content`).toBe(hash);
    }
  });

  it("draws every Malayalam cluster exactly as production does (ghost outline and strokes)", () => {
    expect(differing(golden.clusters, now.clusters)).toEqual([]);
  });

  it("segments and draws real Malayalam words exactly as production does", () => {
    expect(differing(golden.words, now.words)).toEqual([]);
  });
});
