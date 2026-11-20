/**
 * Snapshot of everything the runtime derives for Malayalam - shared by the freeze test and its generator.
 *
 * Malayalam is the project's published, human-approved language. This captures, as short hashes, what a
 * visitor actually sees for it: for every cluster in its glyph data, the ghost outline the runtime builds
 * (`resolveSegments`) and the strokes it draws (a recorded stroke, or one composed from parts); the same for a
 * set of real words, including legacy chillu spellings and split vowels; and the data files themselves.
 *
 * `tests/freeze/malayalam-golden.json` holds this snapshot as produced by `origin/master`'s code and data.
 * `tests/malayalam-freeze.test.js` re-takes it from the working tree and fails on any difference, naming the
 * clusters that moved. Shared code may change freely - Malayalam's output may not.
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

/** Words that exercise segmentation, prefix marks, split vowels, chillus (both spellings), conjunct chains,
 * digits, spaces and punctuation. */
export const WORDS = [
  "അമ്മ",
  "നന്ദി",
  "മലയാളം",
  "ആലയം",
  "ക്ഷമിക്കണം",
  "ജയശ്രീ",
  "നോവ്",
  "ധൃഷ്ടദ്യുമ്നൻ",
  "പ്രദ്യുമ്നൻ",
  "കൊച്ചി",
  "കോഴിക്കോട്",
  "മോഹൻലാൽ",
  "ചന്ദ്രൻ",
  "ഗൗരി",
  "കേരളം",
  "വൈകുന്നേരം",
  "ത്സ്യം",
  "ഉത്തരവാദിത്വം",
  "പത്രപ്രവർത്തകൻ",
  "ശ്രീനാരായണഗുരു",
  "അവൻ",
  "അവന്‍", // അവന്‍ - chillu spelled as consonant + virama + ZWJ
  "അവൾ",
  "അവള്‍",
  "നിൻറെ",
  "മഴ പെയ്യുന്നു, വരൂ!",
  "ഞാൻ ഇന്ന് വരും",
  "പുസ്തകം",
  "വിദ്യാഭ്യാസം",
  "സ്വാതന്ത്ര്യം",
  "ക്രിസ്തുമസ്",
  "ഉണ്ണിക്കൃഷ്ണൻ",
  "൧൨൩ 123",
  "ഒരു, രണ്ട്; മൂന്ന്.",
  "ശബ്ദം",
  "ജ്ഞാനം",
  "അദ്ധ്യാപകൻ",
  "കൈരളി",
];

let instances = 0; // deterministic cache-bust: one fresh module instance per snapshot
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
/** Hash of a text file with Windows line endings normalised, so a CRLF checkout does not read as a change. */
const textSha = (buffer) => sha(buffer.toString("utf-8").replace(/\r\n/g, "\n"));
const short = (text) => sha(text).slice(0, 16);

/** `JSON.stringify` with sorted object keys, so a hash does not depend on the order keys were written in. */
export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

/** Files whose content must not change: Malayalam's recorded strokes, processed strokes and character inventory. */
const BYTE_FILES = [
  "js/src/stroke-data.raw.json",
  "js/src/stroke-data.json",
  "python/src/jayasree/_chars.py",
  "python/tests/test_chars_malayalam.py",
  "python/tests/snapshots/stroke_data_raw_snapshot.json",
];

/**
 * Take the snapshot of the Malayalam files and runtime found under `root`.
 *
 * @param {string} root - A directory laid out like this repo (needs `js/src/` and the files in BYTE_FILES).
 * @returns {Promise<{ data: Record<string, string>, clusters: Record<string, string>, words: Record<string, string>, stages: string[] }>}
 *   `stages` names the composition steps found on the runtime under test, in the order they are tried.
 */
export async function snapshot(root) {
  const read = (rel) => readFileSync(join(root, rel));
  const glyphData = JSON.parse(read("js/src/glyph-data.json").toString("utf-8"));
  const strokeData = JSON.parse(read("js/src/stroke-data.json").toString("utf-8"));

  // Its own module instance (STROKE_LIBRARY is module-global), so a snapshot of one tree never sees another's.
  const url = `${pathToFileURL(join(root, "js/src/index.js")).href}?freeze=${++instances}`;
  const { STROKE_LIBRARY, _internal } = await import(url);
  for (const key of Object.keys(STROKE_LIBRARY)) delete STROKE_LIBRARY[key];
  Object.assign(STROKE_LIBRARY, strokeData);

  const { clusters, marks, legacyEncodings } = glyphData;

  // What the runtime draws for a segment: a recorded stroke, else the first composition step that succeeds
  // (index.js buildStage: STROKE_LIBRARY ?? tryComposeStroke ?? tryComposeContextualForm ??
  // tryComposeFromCharacters). Mirrored by hand because buildStage is DOM code - so a reordering *inside*
  // buildStage itself cannot be detected here (see CONTRIBUTING's "What it does not cover"). A step that production's runtime
  // does not have yet (the contextual-form step arrived with Hindi) is skipped; the freeze test asserts that
  // the runtime under test has every step, so a rename or removal cannot silently drop one.
  const steps = ["tryComposeStroke", "tryComposeContextualForm", "tryComposeFromCharacters"].filter(
    (name) => typeof _internal[name] === "function"
  );
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
  data["js/src/glyph-data.json#clusters"] = short(canonical(clusters));
  data["js/src/glyph-data.json#marks"] = short(canonical(marks));

  const clusterHashes = {};
  for (const cluster of Object.keys(clusters).sort()) clusterHashes[cluster] = hashText(cluster);
  const wordHashes = {};
  for (const word of WORDS) wordHashes[word] = hashText(word);
  return { data, clusters: clusterHashes, words: wordHashes, stages: steps };
}
