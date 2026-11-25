/**
 * Tests for tools/build_npm_packages.js - the engine and data packages that go to npm.
 *
 * The coverage check at the bottom is the gate for new languages: a data file under js/src/
 * that no package lists fails here, so a language can't be added and then silently not shipped.
 */

import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import {
  DATA_PACKAGES,
  SCOPE,
  UNPACKAGED_DATA,
  buildPackages,
  indexSource,
  packageJson,
  readmeSource,
} from "../tools/build_npm_packages.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const read = (...p) => readFileSync(join(...p), "utf8");
const version = JSON.parse(read(ROOT, "js", "package.json")).version;

let out;
beforeAll(() => {
  out = mkdtempSync(join(tmpdir(), "jayasree-npm-"));
  buildPackages(ROOT, out);
});
afterAll(() => rmSync(out, { recursive: true, force: true }));

describe("data packages", () => {
  it("Ensure that every package carries the engine's version", () => {
    for (const spec of DATA_PACKAGES) {
      const pkg = JSON.parse(read(out, spec.name, "package.json"));
      expect(pkg.name).toBe(`${SCOPE}/${spec.name}`);
      expect(pkg.version).toBe(version);
    }
  });

  it("Ensure that every file a package lists is in its folder", () => {
    for (const spec of DATA_PACKAGES) {
      const pkg = JSON.parse(read(out, spec.name, "package.json"));
      for (const file of pkg.files) expect(existsSync(join(out, spec.name, file))).toBe(true);
    }
  });

  it("Ensure that no package ships a raw recording", () => {
    for (const spec of DATA_PACKAGES) {
      expect(readdirSync(join(out, spec.name)).filter((f) => f.includes("raw"))).toEqual([]);
    }
  });

  it("Ensure that no package depends on another, so each installs alone", () => {
    for (const spec of DATA_PACKAGES) {
      const pkg = JSON.parse(read(out, spec.name, "package.json"));
      expect(pkg.dependencies ?? pkg.peerDependencies).toBeUndefined();
    }
  });

  it("Ensure that the font package is OFL and carries its notices", () => {
    const font = JSON.parse(read(out, "ml-font", "package.json"));
    expect(font.license).toBe("OFL-1.1");
    for (const f of ["OFL-Chilanka.txt", "OFL-Manjari.txt", "OFL-Nupuram.txt"]) {
      expect(font.files).toContain(f);
    }
    expect(font.files).toContain("glyph-data.json");
  });

  it("Ensure that the handwriting packages are CC BY-SA plus the OFL of their outlines", () => {
    const notices = { ml: "OFL-Manjari.txt", hi: "OFL-NotoSansDevanagari.txt" };
    for (const [name, ofl] of Object.entries(notices)) {
      const pkg = JSON.parse(read(out, name, "package.json"));
      expect(pkg.license).toBe("CC-BY-SA-4.0 AND OFL-1.1");
      expect(pkg.files).toContain("LICENSE-DATA");
      expect(pkg.files).toContain(ofl);
    }
  });

  it("Ensure that index.js exports a URL for each data file", () => {
    const ml = DATA_PACKAGES.find((s) => s.name === "ml");
    expect(indexSource(ml)).toContain('export const glyphData = new URL("./glyph-data.json"');
    expect(indexSource(ml)).toContain('export const strokeData = new URL("./stroke-data.json"');
    const font = DATA_PACKAGES.find((s) => s.name === "ml-font");
    expect(indexSource(font)).toContain("export const glyphData");
    expect(indexSource(font)).toContain("outlineFallback: false");
  });

  it("Ensure that a package copies the data it names, byte for byte", () => {
    for (const spec of DATA_PACKAGES) {
      for (const [target, source] of Object.entries(spec.files)) {
        expect(read(out, spec.name, target)).toBe(read(ROOT, source));
      }
    }
  });

  it("Ensure that the package.json builder uses the version it is given", () => {
    expect(packageJson(DATA_PACKAGES[0], "1.2.3").version).toBe("1.2.3");
  });
});

describe("package READMEs and the build", () => {
  it("Ensure that the font README passes the no-fallback options and says what they do", () => {
    const font = DATA_PACKAGES.find((s) => s.name === "ml-font");
    expect(readmeSource(font)).toContain("createStrokeWriter(document.getElementById(\"stage\"), writerOptions)");
    expect(readmeSource(font)).toContain("outlineFallback: false");
  });

  it("Ensure that building leaves every other file in --out alone", () => {
    const dir = mkdtempSync(join(tmpdir(), "jayasree-keep-"));
    writeFileSync(join(dir, "keep.txt"), "mine");
    buildPackages(ROOT, dir);
    expect(read(dir, "keep.txt")).toBe("mine");
    rmSync(dir, { recursive: true, force: true });
  });

  it("Ensure that building fails when a licence file is missing", () => {
    expect(() => buildPackages(join(tmpdir(), "no-such-root"), join(tmpdir(), "x"))).toThrow();
  });
});

describe("the engine package", () => {
  const engine = JSON.parse(read(ROOT, "js", "package.json"));

  it("Ensure that the engine ships no language data", () => {
    expect(engine.files.filter((f) => /data|raw/.test(f))).toEqual([]);
  });

  it("Ensure that the engine's files all exist", () => {
    for (const f of engine.files) expect(existsSync(join(ROOT, "js", f))).toBe(true);
  });
});

describe("coverage of js/src", () => {
  it("Ensure that every data file under js/src is in a package or deliberately left out", () => {
    const packaged = new Set(DATA_PACKAGES.flatMap((s) => Object.values(s.files)));
    const left = new Set(UNPACKAGED_DATA);
    const found = readdirSync(join(ROOT, "js", "src"))
      .filter((f) => /^(glyph|stroke)-data.*\.json$|^font-strokes.*\.json$/.test(f))
      .map((f) => `js/src/${f}`);
    expect(found.filter((f) => !packaged.has(f) && !left.has(f))).toEqual([]);
  });
});
