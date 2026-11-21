/**
 * Snapshot of everything the runtime derives for Hindi - shared by the freeze test and its generator.
 *
 * Hindi is a shipped, owner-approved language (the owner said "Hindi ships"). Like Malayalam's
 * (`malayalam-snapshot.mjs`) this captures, as short hashes, what a visitor sees: for every cluster in its
 * glyph data, the ghost outline the runtime builds (`resolveSegments`) and the strokes it draws; the same for
 * real Hindi words (conjuncts, half-forms, reph, nukta, vowel signs, dots-last letters, digits, punctuation);
 * and the data files. Unlike Malayalam's, every top-level field of `glyph-data.hi.json` is hashed, so a new or
 * edited field counts as a change.
 *
 * `tests/freeze/hindi-golden.json` holds the snapshot taken when Hindi shipped. `tests/hindi-freeze.test.js`
 * re-takes it from the working tree and fails on any difference. Shared code may change freely - Hindi's
 * output may not. Malayalam's own files (`malayalam-snapshot.mjs`, its golden) are deliberately left alone.
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { canonical } from "./malayalam-snapshot.mjs";

export { canonical };

/** Words that exercise segmentation, conjuncts, half-forms, reph, nukta letters, vowel signs, dots-last
 * letters, digits, spaces and punctuation. */
export const WORDS = [
  "भारत",
  "नमस्ते",
  "हिन्दी",
  "धन्यवाद",
  "क्षमा",
  "ज्ञान",
  "श्रीमान",
  "प्रेम",
  "कर्म",
  "पुस्तक",
  "विद्यालय",
  "स्वतंत्रता",
  "द्वारा",
  "बच्चों",
  "ख़बर",
  "ज़िंदगी",
  "फ़ोटो",
  "कृष्ण",
  "राष्ट्र",
  "उन्नति",
  "वाङ्मय",
  "अंग्रेज़ी",
  "चाँद",
  "ऑफ़िस",
  "सुन्दर",
  "ट्रेन",
  "डॉक्टर",
  "ऋषि",
  "दुःख",
  "आईना",
  "ऊपर",
  "ऐसा",
  "औरत",
  "संस्कृत",
  "विज्ञान",
  "अध्यक्ष",
  "मैं हिंदी बोलता हूँ।",
  "क्या, आप ठीक हैं?",
  "१२३ 123",
  "ङ्ख ख़",
];

let instances = 0; // deterministic cache-bust: one fresh module instance per snapshot
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
/** Hash of a text file with Windows line endings normalised, so a CRLF checkout does not read as a change. */
const textSha = (buffer) => sha(buffer.toString("utf-8").replace(/\r\n/g, "\n"));
const short = (text) => sha(text).slice(0, 16);

/** Files whose content must not change: Hindi's recorded strokes, processed strokes, inventory and pins. */
const BYTE_FILES = [
  "js/src/stroke-data.hi.raw.json",
  "js/src/stroke-data.hi.json",
  "python/src/jayasree/_chars_hi.py",
  "python/tests/test_chars_hi.py",
  "python/tests/snapshots/stroke_data_raw_snapshot.hi.json",
];

/** The composition steps the runtime tries after a recorded stroke, in order (index.js `buildStage`). */
export const STAGES = ["tryComposeStroke", "tryComposeContextualForm", "tryComposeFromCharacters"];

/**
 * Take the snapshot of the Hindi files and runtime found under `root`.
 *
 * @param {string} root - A directory laid out like this repo (needs `js/src/` and the files in BYTE_FILES).
 * @returns {Promise<{ data: Record<string, string>, clusters: Record<string, string>, words: Record<string, string>, stages: string[] }>}
 *   `stages` names the composition steps found on the runtime under test, in the order they are tried.
 */
export async function snapshot(root) {
  const read = (rel) => readFileSync(join(root, rel));
  const glyphData = JSON.parse(read("js/src/glyph-data.hi.json").toString("utf-8"));
  const strokeData = JSON.parse(read("js/src/stroke-data.hi.json").toString("utf-8"));

  // Its own module instance (STROKE_LIBRARY is module-global), so a snapshot never sees another tree's.
  const url = `${pathToFileURL(join(root, "js/src/index.js")).href}?hifreeze=${++instances}`;
  const { STROKE_LIBRARY, _internal } = await import(url);
  for (const key of Object.keys(STROKE_LIBRARY)) delete STROKE_LIBRARY[key];
  Object.assign(STROKE_LIBRARY, strokeData);

  const { clusters, marks, legacyEncodings } = glyphData;

  // What the runtime draws for a segment: a recorded stroke, else the first composition step that succeeds.
  // Mirrored by hand because buildStage is DOM code (see CONTRIBUTING's "What it does not cover").
  const steps = STAGES.filter((name) => typeof _internal[name] === "function");
  const strokesFor = (cluster) => {
    let entry = STROKE_LIBRARY[cluster];
    for (const name of steps) entry ??= _internal[name](cluster, glyphData);
    return entry?.strokes?.map((s) => s.d) ?? null;
  };

  /** Hash of the ghost outline and strokes for every segment `text` resolves to. */
  const hashText = (text) => {
    const segments = _internal.resolveSegments(text, clusters, marks, legacyEncodings);
    return short(
      canonical(
        segments.map((seg) => ({
          cluster: seg.cluster,
          advance: seg.entry.advance,
          glyphs: seg.entry.glyphs,
          strokes: strokesFor(seg.cluster),
        }))
      )
    );
  };

  const data = Object.fromEntries(BYTE_FILES.map((rel) => [rel, textSha(read(rel))]));
  for (const [field, value] of Object.entries(glyphData)) {
    data[`js/src/glyph-data.hi.json#${field}`] = short(canonical(value));
  }

  const clusterHashes = {};
  for (const cluster of Object.keys(clusters).sort()) clusterHashes[cluster] = hashText(cluster);
  const wordHashes = {};
  for (const word of WORDS) wordHashes[word] = hashText(word);
  return { data, clusters: clusterHashes, words: wordHashes, stages: steps };
}
