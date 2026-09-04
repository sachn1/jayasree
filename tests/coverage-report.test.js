/**
 * Tests for tools/coverage_report.js - the per-cluster direct/composed/
 * fallback coverage audit (docs/LANGUAGE_ONBOARDING_AGENTS.md's Agent 3
 * pre-/post-recording coverage gate).
 *
 * Synthetic fixtures for the classification logic itself; one real-data
 * sanity check at the bottom mirrors composition-coverage.test.js's own
 * "found a non-trivial number to test against" guard, so a change to the
 * real committed files that silently breaks coverage doesn't go unnoticed
 * just because this file's own fixtures are synthetic.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it } from "vitest";
import { STROKE_LIBRARY } from "../js/src/index.js";
import { classify, computeCoverage, populateStrokeLibrary } from "../tools/coverage_report.js";

beforeEach(() => {
  for (const key of Object.keys(STROKE_LIBRARY)) delete STROKE_LIBRARY[key];
});

describe("classify", () => {
  const glyphData = {
    clusters: {
      A: { glyphs: [{ d: "MA", x: 0, y: 0 }], advance: 100 },
      B: { glyphs: [{ d: "MB", x: 0, y: 0 }], advance: 100 },
      AB: { glyphs: [{ d: "MA", x: 0, y: 0 }, { d: "MB", x: 100, y: 0 }], advance: 200 },
      Am: { glyphs: [{ d: "MA", x: 0, y: 0 }, { d: "Mm", x: 100, y: 0 }], advance: 120 },
    },
    marks: {
      m: { shift: 0, prefix: [], suffix: [{ d: "Mm", x: 0, y: 0 }], trailingWidth: 20 },
    },
  };

  it("reports 'direct' for a cluster with its own recorded stroke", () => {
    STROKE_LIBRARY.A = { strokes: [{ d: "M0 0" }] };
    expect(classify("A", glyphData)).toEqual({ status: "direct" });
  });

  it("reports 'composed' when tryComposeFromCharacters succeeds", () => {
    STROKE_LIBRARY.A = { strokes: [{ d: "M0 0" }] };
    STROKE_LIBRARY.B = { strokes: [{ d: "M0 0" }] };
    expect(classify("AB", glyphData)).toEqual({ status: "composed" });
  });

  it("reports 'composed' when tryComposeStroke succeeds via a mark recipe", () => {
    STROKE_LIBRARY.A = { strokes: [{ d: "M0 0" }] };
    STROKE_LIBRARY.m = { strokes: [{ d: "M0 0" }] };
    expect(classify("Am", glyphData)).toEqual({ status: "composed" });
  });

  it("reports 'fallback' with a reason when the base has no stroke", () => {
    // A has a clusters entry but no recorded/composed stroke - so Am (A's
    // mark composition) can't proceed even though the mark recipe exists.
    const result = classify("Am", glyphData);
    expect(result.status).toBe("fallback");
    expect(result.reason.length).toBeGreaterThan(0);
  });

  it("names the missing base specifically when the base has a stroke gap", () => {
    STROKE_LIBRARY.m = { strokes: [{ d: "M0 0" }] };
    // A still has no stroke - the mark itself is fine, the base isn't.
    const result = classify("Am", glyphData);
    expect(result.status).toBe("fallback");
    expect(result.reason).toContain("A");
  });
});

describe("computeCoverage", () => {
  const glyphData = {
    clusters: {
      A: { glyphs: [{ d: "MA", x: 0, y: 0 }], advance: 100 },
      B: { glyphs: [{ d: "MB", x: 0, y: 0 }], advance: 100 },
      AB: { glyphs: [{ d: "MA", x: 0, y: 0 }, { d: "MB", x: 100, y: 0 }], advance: 200 },
    },
    marks: {},
  };

  it("computes 100% coverage when every cluster resolves", () => {
    STROKE_LIBRARY.A = { strokes: [{ d: "M0 0" }] };
    STROKE_LIBRARY.B = { strokes: [{ d: "M0 0" }] };
    const { total, covered, pct, results } = computeCoverage(glyphData);
    expect(total).toBe(3);
    expect(covered).toBe(3);
    expect(pct).toBe("100.0");
    expect(results.direct).toEqual(expect.arrayContaining(["A", "B"]));
    expect(results.composed).toEqual(["AB"]);
    expect(results.fallback).toEqual([]);
  });

  it("computes partial coverage and lists fallback clusters with reasons", () => {
    STROKE_LIBRARY.A = { strokes: [{ d: "M0 0" }] };
    // B has no stroke - AB can't compose from characters either.
    const { total, covered, pct, results } = computeCoverage(glyphData);
    expect(total).toBe(3);
    expect(covered).toBe(1);
    expect(pct).toBe("33.3");
    expect(results.fallback.map(([cluster]) => cluster).sort()).toEqual(["AB", "B"]);
  });
});

describe("populateStrokeLibrary", () => {
  it("seeds one stub stroke per line of a --simulate-atoms file", () => {
    const path = "/tmp/coverage-report-test-atoms.txt";
    writeAtomsFile(path, ["A", "B", ""]); // trailing blank line should be dropped
    const count = populateStrokeLibrary({ simulateAtoms: path, strokeData: null });
    expect(count).toBe(2);
    expect(STROKE_LIBRARY.A.strokes.length).toBeGreaterThan(0);
    expect(STROKE_LIBRARY.B.strokes.length).toBeGreaterThan(0);
  });

  it("returns 0 and leaves STROKE_LIBRARY empty when neither option is given", () => {
    const count = populateStrokeLibrary({ simulateAtoms: null, strokeData: null });
    expect(count).toBe(0);
    expect(Object.keys(STROKE_LIBRARY)).toEqual([]);
  });
});

// Minimal local file writer so this test file doesn't need a fixtures/ dir
// for two throwaway lines.
function writeAtomsFile(path, lines) {
  writeFileSync(path, lines.join("\n"));
}

describe("real-data sanity", () => {
  const ROOT = fileURLToPath(new URL("..", import.meta.url));
  const glyphData = JSON.parse(readFileSync(`${ROOT}js/src/glyph-data.json`, "utf-8"));
  const strokeData = JSON.parse(readFileSync(`${ROOT}js/src/stroke-data.json`, "utf-8"));

  it("Malayalam's real committed data has full (100%) coverage", () => {
    // Guards this file's own synthetic fixtures against silently drifting
    // from what the real classify()/computeCoverage() logic actually does
    // against real data - and is itself a real, meaningful regression gate
    // (see docs/ROADMAP.md's "Bug-report -> data pipeline"): if a future
    // change ever regresses real coverage below 100%, this test catches it.
    populateStrokeLibrary({ simulateAtoms: null, strokeData: null });
    Object.assign(STROKE_LIBRARY, strokeData);
    const { pct, results } = computeCoverage(glyphData);
    expect(results.fallback).toEqual([]);
    expect(pct).toBe("100.0");
  });
});
