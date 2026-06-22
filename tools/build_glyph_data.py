#!/usr/bin/env python3
"""Build tool: pre-compute SVG glyph paths for all Malayalam characters.

Shapes every base character + all consonant-matra combinations using the
Python shaper (HarfBuzz), then writes a single JSON file that the JS
package bundles. After this runs, the JS package needs no server and no
font at runtime.

Usage:
    python tools/build_glyph_data.py

    # optionally supply a different font (defaults to the bundled Manjari-Regular.ttf):
    python tools/build_glyph_data.py /path/to/MyFont.ttf

Output:
    js/src/glyph-data.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

from malayalam_stroker import shape_word  # noqa: E402

FONT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else str(ROOT / "python" / "tests" / "fixtures" / "Manjari-Regular.ttf")
)

CONSONANTS = list("കഖഗഘങചഛജഝഞടഠഡഢണതഥദധനപഫബഭമയരലവശഷസഹളഴറ")
MATRAS     = list("ാിീുൂൃെേൈൊോൗ")
VIRAMA     = "\u0d4d"

# All inputs to shape — each becomes one entry keyed by its Unicode string
inputs: list[str] = []

# Standalone characters
for ch in (
    "അആഇഈഉഊഋഎഏഐഒഓഔ"   # independent vowels
    + "".join(CONSONANTS)
    + "ൻർൽൾൺ"             # chillu
    + "൦൧൨൩൪൫൬൭൮൯"        # numerals
):
    inputs.append(ch)

# Consonant + matra (all combinations — covers every written syllable)
for c in CONSONANTS:
    for m in MATRAS:
        inputs.append(c + m)

# Conjuncts: consonant + virama + consonant (3-char clusters)
# These are looked up first by segmentText's longest-match logic.
for c1 in CONSONANTS:
    for c2 in CONSONANTS:
        inputs.append(c1 + VIRAMA + c2)

# Special marks shaped against a carrier
for syllable in ["ക്", "കം", "കഃ"]:
    inputs.append(syllable)

# Independent vowels + anusvara/visarga (e.g. അം, അഃ, ആം ...)
INDEPENDENT_VOWELS = list("അആഇഈഉഊഋഎഏഐഒഓഔ")
for v in INDEPENDENT_VOWELS:
    inputs.append(v + "\u0d02")   # + anusvara ം
    inputs.append(v + "\u0d03")   # + visarga ഃ

# All consonants + anusvara / visarga ( കം ഖം ... കഃ ഖഃ ...)
for c in CONSONANTS:
    inputs.append(c + "\u0d02")   # + anusvara
    inputs.append(c + "\u0d03")   # + visarga

# ── shape everything ──────────────────────────────────────────────────────
result: dict = {"meta": None, "clusters": {}}
ok = skipped = 0

for inp in inputs:
    if inp in result["clusters"]:
        continue
    try:
        trace = shape_word(inp, FONT)
    except Exception as exc:
        print(f"  skip {inp!r}: {exc}", file=sys.stderr)
        skipped += 1
        continue

    if result["meta"] is None:
        result["meta"] = {
            "unitsPerEm": trace["unitsPerEm"],
            "ascent":     trace["ascent"],
            "descent":    trace["descent"],
        }

    result["clusters"][inp] = {
        "glyphs":  [{"d": g["d"], "x": g["x"], "y": g["y"]} for g in trace["glyphs"]],
        "advance": trace["totalAdvance"],
    }
    ok += 1

out_path = ROOT / "js" / "src" / "glyph-data.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

size_kb = out_path.stat().st_size // 1024
print(f"Written {out_path.relative_to(ROOT)}  ({size_kb} KB, {ok} clusters, {skipped} skipped)",
      file=sys.stderr)
