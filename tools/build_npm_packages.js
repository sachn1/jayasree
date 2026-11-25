#!/usr/bin/env node
/**
 * Build the npm data packages (`@jayasree-stroke/ml`, `/hi`, `/ml-font`) into `dist-npm/`.
 *
 * The engine (`jayasree`) is published straight from `js/`; each language's data is copied
 * out of `js/src/` here so the data files stay where the demo, tools and tests expect them.
 * Every package takes the engine's version, so one release number covers all of them.
 *
 * Adding a language: add one entry to DATA_PACKAGES. The test in tests/npm-packages.test.js
 * fails while any data file under `js/src/` belongs to no package.
 *
 * Usage (from repo root):
 *   node tools/build_npm_packages.js [--out dist-npm]
 */

import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SCOPE = "@jayasree-stroke";
const REPO_URL = "git+https://github.com/sachn1/jayasree.git";
const OFL_MANJARI = "third-party/OFL-Manjari.txt";
const HANDWRITING_LICENCE =
  "The strokes are CC BY-SA 4.0 (see `LICENSE-DATA`); the glyph outlines are derived from an OFL-licensed font,\n" +
  "whose licence text is in this package. The engine, `jayasree`, is MIT.";
const OFL_FILES = ["third-party/OFL-Chilanka.txt", OFL_MANJARI, "third-party/OFL-Nupuram.txt"];

/**
 * One entry per published data package.
 *
 * `files` maps a file in the package to its source under the repo root. `exports` names what
 * the package's index.js exports (a URL for each file); `extraExport` is a line added to it, and
 * `writerArg`, `note` and `licenceText` are the README's extra argument, note and licence paragraph.
 */
export const DATA_PACKAGES = [
  {
    name: "ml",
    description: "Malayalam glyph outlines and handwriting strokes for jayasree",
    keywords: ["malayalam"],
    license: "CC-BY-SA-4.0 AND OFL-1.1",
    files: {
      "glyph-data.json": "js/src/glyph-data.json",
      "stroke-data.json": "js/src/stroke-data.json",
    },
    exports: { glyphData: "glyph-data.json", strokeData: "stroke-data.json" },
    licenseFiles: ["LICENSE-DATA", OFL_MANJARI],
    licenceText: HANDWRITING_LICENCE,
  },
  {
    name: "hi",
    description: "Hindi glyph outlines and handwriting strokes for jayasree",
    keywords: ["hindi", "devanagari"],
    license: "CC-BY-SA-4.0 AND OFL-1.1",
    files: {
      "glyph-data.json": "js/src/glyph-data.hi.json",
      "stroke-data.json": "js/src/stroke-data.hi.json",
    },
    exports: { glyphData: "glyph-data.json", strokeData: "stroke-data.json" },
    licenseFiles: ["LICENSE-DATA", "third-party/OFL-NotoSansDevanagari.txt"],
    licenceText: HANDWRITING_LICENCE,
  },
  {
    name: "ml-font",
    description: "Malayalam strokes taken from the Chilanka, Manjari and Nupuram fonts, for jayasree",
    keywords: ["malayalam", "chilanka", "manjari", "nupuram"],
    license: "OFL-1.1",
    files: {
      "glyph-data.json": "js/src/glyph-data.json",
      "stroke-data.json": "js/src/stroke-data.font.json",
    },
    exports: { glyphData: "glyph-data.json", strokeData: "stroke-data.json" },
    extraExport: "export const writerOptions = { outlineFallback: false };",
    writerArg: "writerOptions",
    note:
      "\n`writerOptions` is `{ outlineFallback: false }`: a letter these strokes lack gets no pen stroke, never an\n" +
      "outline trace. Don't load this package's strokes together with the handwriting ones; the first loaded wins.\n",
    licenceText:
      "SIL Open Font License 1.1. The strokes are taken from the sources of Chilanka, Manjari and Nupuram\n" +
      "(Swathanthra Malayalam Computing) and the outlines from Manjari; their licence texts and copyright\n" +
      "notices are in this package and must travel with any copy. See `LICENSE-DATA`.",
    licenseFiles: ["LICENSE-DATA", ...OFL_FILES],
  },
];

/** Data files under js/src that belong to a package (the rest of the glob is raw or font input). */
export const UNPACKAGED_DATA = [
  "js/src/stroke-data.raw.json",
  "js/src/stroke-data.hi.raw.json",
  "js/src/font-strokes.ml.json",
];

/**
 * The text of a package's index.js: one exported URL per data file.
 *
 * @param {object} spec - An entry of DATA_PACKAGES.
 * @returns {string}
 */
export function indexSource(spec) {
  const lines = Object.entries(spec.exports).map(
    ([name, file]) => `export const ${name} = new URL("./${file}", import.meta.url);`,
  );
  if (spec.extraExport) lines.push(spec.extraExport);
  return `${lines.join("\n")}\n`;
}

/**
 * A package's package.json as an object.
 *
 * @param {object} spec - An entry of DATA_PACKAGES.
 * @param {string} version - The engine's version, shared by every package.
 * @returns {object}
 */
export function packageJson(spec, version) {
  const files = ["index.js", "README.md", ...Object.keys(spec.files), ...spec.licenseFiles.map((f) => baseName(f))];
  const pkg = {
    name: `${SCOPE}/${spec.name}`,
    version,
    description: spec.description,
    type: "module",
    main: "index.js",
    exports: {
      ".": "./index.js",
      ...Object.fromEntries(Object.keys(spec.files).map((f) => [`./${f}`, `./${f}`])),
    },
    files,
    keywords: ["jayasree", "indic", "stroke-order", "handwriting", ...spec.keywords],
    license: spec.license,
    author: "Sachin Nandakumar",
    repository: { type: "git", url: REPO_URL },
    homepage: "https://github.com/sachn1/jayasree#readme",
    publishConfig: { access: "public" },
  };
  return pkg;
}

function baseName(path) {
  return path.split("/").pop();
}

/**
 * A package's README: how to install and load it, and its licence.
 *
 * @param {object} spec - An entry of DATA_PACKAGES.
 * @returns {string}
 */
export function readmeSource(spec) {
  const name = `${SCOPE}/${spec.name}`;
  const names = Object.keys(spec.exports).join(", ");
  return `# ${name}

${spec.description}. Data for the [\`jayasree\`](https://www.npmjs.com/package/jayasree) engine; install both.

\`\`\`bash
npm install jayasree ${name}
\`\`\`

\`\`\`js
import { createStrokeWriter } from "jayasree";
import { ${names} } from "${name}";

const writer = createStrokeWriter(document.getElementById("stage")${spec.writerArg ? `, ${spec.writerArg}` : ""});
await writer.load(glyphData);
await writer.loadStrokes(strokeData);
\`\`\`
${spec.note ?? ""}
## Licence

${spec.licenceText}
`;
}

/**
 * Write every data package into `outDir`, replacing only its own package folders.
 *
 * @param {string} root - The repo root.
 * @param {string} outDir - Where to write; one folder per package.
 * @returns {string[]} The folders written.
 */
export function buildPackages(root, outDir) {
  const version = JSON.parse(readFileSync(join(root, "js", "package.json"), "utf8")).version;
  const written = [];
  for (const spec of DATA_PACKAGES) {
    const dir = join(outDir, spec.name);
    // Clear only the folder this script writes, so a wrong --out can never delete anything else.
    rmSync(dir, { recursive: true, force: true });
    mkdirSync(dir, { recursive: true });
    for (const [target, source] of Object.entries(spec.files)) {
      cpSync(join(root, source), join(dir, target));
    }
    for (const license of spec.licenseFiles) {
      if (!existsSync(join(root, license))) throw new Error(`${license} is missing`);
      cpSync(join(root, license), join(dir, baseName(license)));
    }
    writeFileSync(join(dir, "index.js"), indexSource(spec));
    writeFileSync(join(dir, "README.md"), readmeSource(spec));
    writeFileSync(join(dir, "package.json"), `${JSON.stringify(packageJson(spec, version), null, 2)}\n`);
    written.push(dir);
  }
  return written;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const flag = process.argv.indexOf("--out");
  const out = resolve(root, flag > 0 ? process.argv[flag + 1] : "dist-npm");
  for (const dir of buildPackages(root, out)) console.log(`built ${dir}`);
}
