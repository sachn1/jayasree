#!/usr/bin/env node
/**
 * Report, for every cluster a language's glyph-data.json defines, whether
 * it resolves to a real traced/composed stroke or falls back to the
 * outline trace - and why, for the fallback case.
 *
 * This is the general-purpose version of the "one-command diagnostic" /
 * "standing coverage gate" docs/ROADMAP.md's "Bug-report -> data pipeline"
 * section describes and flags as not-yet-built. Reuses the exact runtime
 * composition functions (`_internal.tryComposeStroke`/
 * `tryComposeContextualForm`/`tryComposeFromCharacters`) js/src/index.js's
 * `buildStage` calls - this script is not a reimplementation of that logic,
 * just a driver over every cluster instead of the ones one word happens to
 * use.
 *
 * Two uses (see docs/LANGUAGE_ONBOARDING_AGENTS.md's Agent 3 section):
 *
 *   1. Pre-recording (simulated): pass --simulate-atoms <file> (one cluster
 *      string per line - typically Agent 3's planned reduced atom set)
 *      instead of --stroke-data. Every listed atom is treated as if it
 *      already had a trivial recorded stroke, so the report shows whether
 *      the *planned* atom set would be sufficient to cover every cluster
 *      via composition, before anyone spends time actually tracing it.
 *   2. Post-recording (real): pass --stroke-data pointing at the real,
 *      partially-or-fully recorded stroke-data(.raw).json to see actual
 *      current coverage.
 *
 * Usage (from repo root):
 *   node tools/coverage_report.js
 *   node tools/coverage_report.js --glyph-data js/src/glyph-data.hi.json --stroke-data js/src/stroke-data.hi.raw.json
 *   node tools/coverage_report.js --simulate-atoms /tmp/hindi-atoms.txt --glyph-data js/src/glyph-data.hi.json
 *   node tools/coverage_report.js --verbose            # list every fallback cluster
 *   node tools/coverage_report.js --min-coverage 95     # exit 1 if composed+direct % is below this
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { STROKE_LIBRARY, _internal } from "../js/src/index.js";

const { tryComposeStroke, tryComposeContextualForm, tryComposeFromCharacters } = _internal;

const ROOT = fileURLToPath(new URL("..", import.meta.url));

/** @returns {{ glyphData: string, strokeData: string|null, simulateAtoms: string|null, verbose: boolean, minCoverage: number|null }} */
function parseArgs(argv) {
  const opts = {
    glyphData: `${ROOT}js/src/glyph-data.json`,
    strokeData: `${ROOT}js/src/stroke-data.json`,
    simulateAtoms: null,
    verbose: false,
    minCoverage: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--glyph-data") opts.glyphData = argv[++i];
    else if (a === "--stroke-data") opts.strokeData = argv[++i];
    else if (a === "--simulate-atoms") {
      opts.simulateAtoms = argv[++i];
      opts.strokeData = null; // simulation replaces real stroke data, not adds to it
    } else if (a === "--verbose") opts.verbose = true;
    else if (a === "--min-coverage") opts.minCoverage = Number(argv[++i]);
    else {
      console.error(`Unknown argument: ${a}`);
      process.exit(2);
    }
  }
  return opts;
}

function loadJson(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

/**
 * Populate STROKE_LIBRARY for the report - either real recorded strokes, or
 * a trivial stub per atom listed in a --simulate-atoms file.
 */
function populateStrokeLibrary(opts) {
  for (const key of Object.keys(STROKE_LIBRARY)) delete STROKE_LIBRARY[key];
  if (opts.simulateAtoms) {
    const atoms = readFileSync(opts.simulateAtoms, "utf-8")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    for (const atom of atoms) STROKE_LIBRARY[atom] = { strokes: [{ d: "M0 0 L1 0" }] };
    return atoms.length;
  }
  if (opts.strokeData) {
    const strokeData = loadJson(opts.strokeData);
    Object.assign(STROKE_LIBRARY, strokeData);
    return Object.keys(strokeData).length;
  }
  return 0;
}

function classify(cluster, glyphData) {
  if (STROKE_LIBRARY[cluster]?.strokes?.length) return { status: "direct" };
  const composed =
    tryComposeStroke(cluster, glyphData) ??
    tryComposeContextualForm(cluster, glyphData) ??
    tryComposeFromCharacters(cluster, glyphData);
  if (composed?.strokes?.length) return { status: "composed" };
  return { status: "fallback", reason: fallbackReason(cluster, glyphData) };
}

/** Best-effort explanation for why a cluster couldn't compose - mirrors the
 * checks tryComposeStroke/tryComposeContextualForm/tryComposeFromCharacters
 * themselves make. */
function fallbackReason(cluster, glyphData) {
  const { clusters, marks, contextualForms } = glyphData;
  if (![...cluster].every((ch) => STROKE_LIBRARY[ch] || clusters[ch])) {
    return "contains a character with no glyph-data entry at all";
  }
  for (const markLen of [2, 1]) {
    if (cluster.length <= markLen) continue;
    const baseKey = cluster.slice(0, -markLen);
    const markKey = cluster.slice(-markLen);
    if (marks[markKey] && !STROKE_LIBRARY[baseKey]) {
      return `base ${JSON.stringify(baseKey)} has no recorded/composed stroke yet`;
    }
    if (marks[markKey] && STROKE_LIBRARY[baseKey]) {
      return `mark ${JSON.stringify(markKey)} recipe exists but composition itself failed - investigate directly`;
    }
  }
  const chars = [...cluster];
  if (contextualForms && chars.length === 3 && clusters[cluster]?.glyphs.length === 2) {
    const trigger = chars[0] + chars[1];
    if (contextualForms[trigger] && !STROKE_LIBRARY[trigger]) {
      return `contextual form ${JSON.stringify(trigger)} (${contextualForms[trigger].role}) has no recorded stroke yet`;
    }
    if (contextualForms[trigger] && STROKE_LIBRARY[trigger]) {
      return `contextual form ${JSON.stringify(trigger)} recipe exists but composition itself failed - investigate directly`;
    }
  }
  if (chars.length !== (clusters[cluster]?.glyphs.length ?? -1)) {
    return "character count doesn't match glyph count (a character contributes >1 glyph) - per-character composition doesn't apply";
  }
  return "no matching mark recipe and no clean per-character decomposition";
}

/**
 * Classify every cluster in `glyphData.clusters` against the *current*
 * contents of STROKE_LIBRARY (caller populates it first - real strokes or
 * simulated stubs, see `populateStrokeLibrary`). Pure with respect to its
 * arguments beyond that global, which is how the real runtime
 * (`js/src/index.js`) itself works too - not reproduced here as a design
 * flaw, matched deliberately so this tool exercises the real code path.
 *
 * @param {object} glyphData
 * @returns {{ total: number, covered: number, pct: string, results: { direct: string[], composed: string[], fallback: [string, string][] } }}
 */
export function computeCoverage(glyphData) {
  const clusterKeys = Object.keys(glyphData.clusters);
  const results = { direct: [], composed: [], fallback: [] };
  for (const cluster of clusterKeys) {
    const r = classify(cluster, glyphData);
    results[r.status].push(r.status === "fallback" ? [cluster, r.reason] : cluster);
  }
  const total = clusterKeys.length;
  const covered = results.direct.length + results.composed.length;
  const pct = total ? ((covered / total) * 100).toFixed(1) : "0.0";
  return { total, covered, pct, results };
}

export { classify, fallbackReason, populateStrokeLibrary };

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const glyphData = loadJson(opts.glyphData);
  const seeded = populateStrokeLibrary(opts);
  const { total, covered, pct, results } = computeCoverage(glyphData);

  const label = opts.simulateAtoms ? "simulated" : "real";
  console.log(`Coverage report (${label}) - ${opts.glyphData}`);
  console.log(`  seeded ${seeded} ${opts.simulateAtoms ? "simulated atoms" : "recorded strokes"}`);
  console.log(`  ${total} total clusters`);
  console.log(`  ${results.direct.length} direct, ${results.composed.length} composed, ${results.fallback.length} fallback`);
  console.log(`  coverage: ${covered}/${total} (${pct}%)`);

  if (opts.verbose && results.fallback.length) {
    console.log("\nFallback clusters:");
    for (const [cluster, reason] of results.fallback) {
      console.log(`  ${JSON.stringify(cluster)} - ${reason}`);
    }
  }

  if (opts.minCoverage != null && Number(pct) < opts.minCoverage) {
    console.error(`\nFAIL: coverage ${pct}% is below --min-coverage ${opts.minCoverage}%`);
    process.exit(1);
  }
}

// Only run the CLI when executed directly (`node coverage_report.js`), not
// when imported by tests/coverage-report.test.js.
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
