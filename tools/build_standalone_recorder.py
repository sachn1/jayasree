#!/usr/bin/env python3
"""Bundle stroke-recorder.html + glyph-data.json into a single self-contained file.

The output can be opened directly in any browser (file://) - no server needed.
Copy it to your tablet once; it works fully offline.

The generated file embeds a content hash of its stroke-recorder.{html,css,js}
+ favicon.svg sources as an HTML comment, so staleness (editing the sources
without regenerating) is always detectable on demand:

    python tools/build_standalone_recorder.py --check

--lang selects which language's glyph-data(.raw)/stroke-data.raw.json get
bundled (default: malayalam, matching every other --lang-aware tool in
tools/ - see docs/LANGUAGE_ONBOARDING_AGENTS.md's Phase 0). The output
filename gets the same `.{code}` suffix data_paths() already uses for
every other language's committed files, so a second language's standalone
recorder never collides with Malayalam's - unsuffixed stays
stroke-recorder-standalone.html for backward compatibility.

Usage (from repo root):
    python tools/build_standalone_recorder.py
    # → tools/stroke-recorder-standalone.html
    python tools/build_standalone_recorder.py --lang hindi
    # → tools/stroke-recorder-standalone.hi.html
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

from jayasree.languages import LANGUAGES, data_paths, get_language  # noqa: E402

HTML_SRC = ROOT / "tools" / "stroke-recorder.html"
CSS_SRC = ROOT / "tools" / "stroke-recorder.css"
JS_SRC = ROOT / "tools" / "stroke-recorder.js"
FAVICON_SRC = ROOT / "favicon.svg"

_HASH_COMMENT = "<!-- source-hash: {} (do not edit; run tools/build_standalone_recorder.py) -->"
_HASH_RE = re.compile(r"<!-- source-hash: ([0-9a-f]+)")


def _out_path(lang_name: str) -> Path:
    """Return the standalone-recorder output path for `--lang lang_name`.

    Unsuffixed for `malayalam` (backward compatible with the existing
    committed/documented filename); `.{code}`-suffixed for everything else,
    mirroring `languages.data_paths()`'s own convention.
    """
    lang = get_language(lang_name)
    is_primary = lang_name == "malayalam"
    suffix = "" if is_primary else f".{lang.code}"
    return ROOT / "tools" / f"stroke-recorder-standalone{suffix}.html"


def _source_hash() -> str:
    """Hash the stroke-recorder source files (+ favicon) together."""
    combined = (
        HTML_SRC.read_bytes()
        + CSS_SRC.read_bytes()
        + JS_SRC.read_bytes()
        + FAVICON_SRC.read_bytes()
    )
    return hashlib.sha256(combined).hexdigest()[:16]


def build(lang_name: str = "malayalam") -> None:
    """Regenerate the standalone recorder for `--lang lang_name` from current sources."""
    lang = get_language(lang_name)
    paths = data_paths(lang)
    out = _out_path(lang_name)

    html = HTML_SRC.read_text(encoding="utf-8")
    css = CSS_SRC.read_text(encoding="utf-8")
    js = JS_SRC.read_text(encoding="utf-8")
    glyph_data = paths.glyph_data.read_text(encoding="utf-8")
    stroke_data_raw = (
        paths.stroke_data_raw.read_text(encoding="utf-8")
        if paths.stroke_data_raw.exists()
        else "{}"
    )

    # Inline CSS
    html = re.sub(
        r'<link\s+rel="stylesheet"\s+href="stroke-recorder\.css"\s*/?>',
        f"<style>\n{css}\n</style>",
        html,
    )

    # Inline the favicon as a data URI - an external ../favicon.svg reference
    # would break once this file is copied somewhere on its own (the whole
    # point of "standalone").
    favicon_b64 = base64.b64encode(FAVICON_SRC.read_bytes()).decode("ascii")
    html = re.sub(
        r'<link\s+rel="icon"[^>]*href="\.\./favicon\.svg"\s*/?>',
        f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{favicon_b64}" />',
        html,
    )

    # Inject glyph-data and the current stroke-data.raw.json as pre-loaded JS
    # variables before the main script, then patch the drop-zone so it
    # auto-loads on page open - bundling the raw strokes too (not just the
    # glyph outlines) means the reduced-set filter and "already recorded"
    # checkmarks are correct immediately, with no manual "Load existing
    # strokes" step needed before recording the remaining gaps.
    preload_script = f"""<script>
// Data bundled at build time - no file drop needed.
const BUNDLED_GLYPH_DATA = {glyph_data};
const BUNDLED_STROKE_DATA = {stroke_data_raw};
</script>"""

    autoload_patch = """<script>
// Auto-load bundled data once the recorder script has initialised.
window.addEventListener("DOMContentLoaded", () => {
  if (typeof BUNDLED_STROKE_DATA !== "undefined") {
    existingStrokeData = BUNDLED_STROKE_DATA;
    const count = Object.keys(existingStrokeData).length;
    document.getElementById("merge-status").textContent =
      `✓ ${count} existing cluster(s) loaded - export will merge`;
  }
  if (typeof BUNDLED_GLYPH_DATA !== "undefined") {
    parseGlyphData(JSON.stringify(BUNDLED_GLYPH_DATA));
    // Land directly on the first not-yet-recorded atom instead of index 0
    // (almost always already-recorded) - removes any guesswork about where
    // to start.
    document.getElementById("next-missing-btn").click();
  }
});
</script>"""

    # Inline JS (replace the external script tag).
    # Use a callable replacement to avoid re interpreting backslashes in JS source.
    inline_js = f"{preload_script}\n<script>\n{js}\n</script>\n{autoload_patch}"
    html = re.sub(
        r'<script\s+src="stroke-recorder\.js"[^>]*></script>',
        lambda _: inline_js,
        html,
    )

    html = re.sub(r"(<html[^>]*>)", rf"\1\n{_HASH_COMMENT.format(_source_hash())}", html, count=1)

    out.write_text(html, encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"Written {out.relative_to(ROOT)}  ({size_kb:.0f} KB)")
    print("Copy this single file to your tablet - opens offline in any browser.")


def check(lang_name: str = "malayalam") -> None:
    """Exit non-zero with a clear message if `--lang lang_name`'s standalone file is stale."""
    out = _out_path(lang_name)
    if not out.exists():
        print(f"STALE: {out.relative_to(ROOT)} does not exist yet.", file=sys.stderr)
        print(
            f"Regenerate with: python tools/build_standalone_recorder.py --lang {lang_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    existing = out.read_text(encoding="utf-8")
    m = _HASH_RE.search(existing)
    current = _source_hash()
    if not m or m.group(1) != current:
        print(
            f"STALE: {out.relative_to(ROOT)} is out of sync with stroke-recorder.{{html,css,js}}.",
            file=sys.stderr,
        )
        print(
            f"Regenerate with: python tools/build_standalone_recorder.py --lang {lang_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"{out.relative_to(ROOT)} is in sync with its sources.")


def main() -> None:
    """Parse CLI args and dispatch to `build()` or `check()`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the standalone file is in sync instead of regenerating it",
    )
    parser.add_argument(
        "--lang",
        default="malayalam",
        choices=sorted(LANGUAGES),
        help="Registry key from jayasree.languages.LANGUAGES (default: malayalam).",
    )
    args = parser.parse_args()
    check(args.lang) if args.check else build(args.lang)


if __name__ == "__main__":
    main()
