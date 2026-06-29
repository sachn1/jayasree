#!/usr/bin/env python3
"""Bundle stroke-recorder.html + glyph-data.json into a single self-contained file.

The output can be opened directly in any browser (file://) — no server needed.
Copy it to your tablet once; it works fully offline.

Usage (from repo root):
    python tools/build_standalone_recorder.py
    # → tools/stroke-recorder-standalone.html
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_SRC = ROOT / "tools" / "stroke-recorder.html"
CSS_SRC = ROOT / "tools" / "stroke-recorder.css"
JS_SRC = ROOT / "tools" / "stroke-recorder.js"
GLYPH_DATA = ROOT / "js" / "src" / "glyph-data.json"
OUT = ROOT / "tools" / "stroke-recorder-standalone.html"


def main() -> None:
    html = HTML_SRC.read_text(encoding="utf-8")
    css = CSS_SRC.read_text(encoding="utf-8")
    js = JS_SRC.read_text(encoding="utf-8")
    glyph_data = GLYPH_DATA.read_text(encoding="utf-8")

    # Inline CSS
    html = re.sub(
        r'<link\s+rel="stylesheet"\s+href="stroke-recorder\.css"\s*/?>',
        f"<style>\n{css}\n</style>",
        html,
    )

    # Inject glyph-data as a pre-loaded JS variable before the main script,
    # then patch the drop-zone so it auto-loads on page open.
    preload_script = f"""<script>
// Glyph data bundled at build time — no file drop needed.
const BUNDLED_GLYPH_DATA = {glyph_data};
</script>"""

    autoload_patch = """<script>
// Auto-load bundled data once the recorder script has initialised.
window.addEventListener("DOMContentLoaded", () => {
  if (typeof BUNDLED_GLYPH_DATA !== "undefined") {
    parseGlyphData(JSON.stringify(BUNDLED_GLYPH_DATA));
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

    OUT.write_text(html, encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"Written {OUT.relative_to(ROOT)}  ({size_kb:.0f} KB)")
    print("Copy this single file to your tablet — opens offline in any browser.")


if __name__ == "__main__":
    main()
