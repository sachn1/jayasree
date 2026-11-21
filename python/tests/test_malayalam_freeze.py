"""Malayalam freeze, Python side: shared build-time code must still produce Malayalam's data.

The JS half (``tests/malayalam-freeze.test.js``) pins what the runtime draws. This pins what the
Python tools put *into* the data files, so a change to shared code - shaping, centering, smoothing,
ghost-guided straightening - cannot quietly alter Malayalam's published letters.

Each test re-derives a deterministic sample of Malayalam's committed ``js/src`` data from its
sources (the Manjari font, the recorded strokes) with today's code and requires an exact match.
Sampling keeps the run to seconds; ``make build-glyph-data`` / ``make process-strokes`` would
regenerate everything.

If Malayalam is *supposed* to change, update the committed data and the ``tests/freeze`` golden in
that same, reviewed PR - never to make this test pass.
"""

from __future__ import annotations

import hashlib
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_glyph_data  # noqa: E402
import process_strokes  # noqa: E402

from jayasree import shape_word  # noqa: E402
from jayasree.languages import get_language  # noqa: E402

JS_SRC = ROOT / "js" / "src"
LANG = get_language("malayalam")

#: Shaping is cheap, so every 5th cluster (about 400) is re-derived. Stroke processing is not, so
#: only atoms whose name hashes into 1 of ATOM_BUCKETS are (about 20): chosen by the *name*, not by
#: position, so adding or removing an atom elsewhere does not reshuffle which ones are covered.
CLUSTER_STRIDE = 5
ATOM_BUCKETS = 18


def _in_atom_sample(atom: str) -> bool:
    """Whether `atom` is one of the deterministically sampled atoms."""
    return int(hashlib.sha1(atom.encode("utf-8")).hexdigest(), 16) % ATOM_BUCKETS == 0


@pytest.fixture(scope="module")
def glyph_data() -> dict:
    """Malayalam's committed glyph data."""
    return json.loads((JS_SRC / "glyph-data.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def font() -> str:
    """Path to Malayalam's bundled ghost font."""
    path = LANG.resolved_default_font()
    assert path is not None, "Malayalam must have a bundled default font"
    return str(path)


def test_shaping_reproduces_committed_clusters(glyph_data: dict, font: str) -> None:
    """Re-shaping a sample of clusters gives the committed glyphs, positions and advances."""
    clusters = glyph_data["clusters"]
    mismatched = []
    for cluster in sorted(clusters)[::CLUSTER_STRIDE]:
        trace = shape_word(cluster, font)
        shaped = {
            "glyphs": [{"d": g["d"], "x": g["x"], "y": g["y"]} for g in trace["glyphs"]],
            "advance": trace["totalAdvance"],
        }
        if shaped != clusters[cluster]:
            mismatched.append(cluster)
    assert mismatched == []


def test_marks_table_reproduces_committed(glyph_data: dict, font: str) -> None:
    """The mark recipes (prefix/suffix glyphs, shifts, widths) rebuild to the committed table."""
    chars = LANG.chars()
    marks = build_glyph_data._build_marks(build_glyph_data._composable_marks(LANG, chars), font)
    assert marks == glyph_data["marks"]


def test_stroke_processing_reproduces_committed_strokes(glyph_data: dict) -> None:
    """Centering, smoothing and straightening a sample of atoms gives the committed strokes.

    Runs the same per-cluster function `tools/process_strokes.py`'s main() runs, with the stages of
    the real preset, so there is no copy of its loop here to drift out of step. The sample is about
    6% of the recorded atoms (chosen by name, see `_in_atom_sample`), so a regression that touches
    only unsampled atoms is caught by the byte hashes of the committed files instead, not here.
    An atom the glyph data has no cluster for would run only the stages that need no font outline,
    exactly as in main() (none is in the sample today).
    """
    stages = {**process_strokes.PRESETS["malayalam"]}
    stages["expand"] = False  # composition of other clusters is not part of re-processing an atom
    args = Namespace(**stages)
    raw = json.loads((JS_SRC / "stroke-data.raw.json").read_text(encoding="utf-8"))
    committed = json.loads((JS_SRC / "stroke-data.json").read_text(encoding="utf-8"))
    atoms = [a for a in sorted(raw) if a != "_remarks"]
    assert len(atoms) > 200, "the data's shape changed: far fewer atoms than expected"
    sample = [a for a in atoms if _in_atom_sample(a)]
    assert len(sample) >= 8, "the sample is too small to mean anything"
    mismatched = []
    for atom in sample:
        processed = process_strokes._process_cluster_strokes(
            atom, raw[atom], glyph_data, args, LANG.code
        )
        if processed != committed.get(atom, {}).get("strokes"):
            mismatched.append(atom)
    assert mismatched == [], (
        "Malayalam strokes changed. If no code changed, a dependency bump (numpy, scipy, "
        "svgpathtools) may have shifted a digit; otherwise shared code now alters Malayalam."
    )
