"""Hindi freeze, Python side: shared build-time code must still produce Hindi's data.

The JS half (``tests/hindi-freeze.test.js``) pins what the runtime draws. This pins what the Python
tools put *into* the data files, so a change to shared code - shaping, centering, smoothing, the
cleanup - cannot quietly alter Hindi's shipped letters, and pins the recorded strokes themselves.

Each test re-derives a deterministic sample of Hindi's committed ``js/src`` data from its sources
(the Noto Sans Devanagari font, the recorded strokes) with today's code and requires an exact match.

If Hindi is *supposed* to change, update the committed data, the snapshot and the ``tests/freeze``
golden in that same, owner-approved PR - never to make this test pass.
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
from validate_data import build_snapshot  # noqa: E402

from jayasree import shape_word  # noqa: E402
from jayasree.languages import get_language  # noqa: E402

JS_SRC = ROOT / "js" / "src"
SNAPSHOT = Path(__file__).parent / "snapshots" / "stroke_data_raw_snapshot.hi.json"
LANG = get_language("hindi")

#: Every 20th cluster is re-shaped, and atoms whose *name* hashes into 1 of ATOM_BUCKETS are
#: re-processed - by name, not position, so adding an atom elsewhere does not reshuffle the sample.
CLUSTER_STRIDE = 20
ATOM_BUCKETS = 12


def _in_atom_sample(atom: str) -> bool:
    """Whether `atom` is one of the deterministically sampled atoms."""
    return int(hashlib.sha1(atom.encode("utf-8")).hexdigest(), 16) % ATOM_BUCKETS == 0


@pytest.fixture(scope="module")
def glyph_data() -> dict:
    """Hindi's committed glyph data."""
    return json.loads((JS_SRC / "glyph-data.hi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def font() -> str:
    """Path to Hindi's bundled ghost font."""
    path = LANG.resolved_default_font()
    assert path is not None, "Hindi must have a bundled default font"
    return str(path)


def test_recorded_strokes_match_the_signed_off_snapshot() -> None:
    """Every recorded Hindi atom is present and byte-identical to what was signed off."""
    raw = json.loads((JS_SRC / "stroke-data.hi.raw.json").read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    current = build_snapshot(raw)
    assert len(snapshot) >= 183, "the sign-off snapshot should cover every recorded atom"
    assert sorted(set(snapshot) - set(current)) == [], "recorded atoms went missing"
    assert sorted(c for c in snapshot if current.get(c) != snapshot[c]) == [], (
        "recorded Hindi strokes changed after sign-off: re-recording needs the owner's approval, "
        "then `python3 tools/validate_data.py --update-snapshot --lang hi`"
    )


def test_shaping_reproduces_committed_clusters(glyph_data: dict, font: str) -> None:
    """Re-shaping a sample of clusters gives the committed glyphs, positions and advances."""
    # Only those fields: Hindi adds more to some clusters (markNudge), which the JS freeze pins.
    clusters = glyph_data["clusters"]
    mismatched = []
    for cluster in sorted(clusters)[::CLUSTER_STRIDE]:
        trace = shape_word(cluster, font)
        shaped = {
            "glyphs": [{"d": g["d"], "x": g["x"], "y": g["y"]} for g in trace["glyphs"]],
            "advance": trace["totalAdvance"],
        }
        committed = {key: clusters[cluster][key] for key in shaped}  # Hindi adds `markNudge` too
        if shaped != committed:
            mismatched.append(cluster)
    assert mismatched == []


def test_stroke_processing_reproduces_committed_strokes(glyph_data: dict) -> None:
    """Processing a sample of atoms (cleanup included) gives the committed strokes byte for byte."""
    args = Namespace(center=True, smooth=True, straighten=True)
    raw = json.loads((JS_SRC / "stroke-data.hi.raw.json").read_text(encoding="utf-8"))
    committed = json.loads((JS_SRC / "stroke-data.hi.json").read_text(encoding="utf-8"))
    atoms = [a for a in sorted(raw) if a != "_remarks"]
    assert len(atoms) >= 183, "the data's shape changed: fewer atoms than were signed off"
    sample = [a for a in atoms if _in_atom_sample(a)]
    assert len(sample) >= 8, "the sample is too small to mean anything"
    mismatched = [
        atom
        for atom in sample
        if process_strokes._process_cluster_strokes(atom, raw[atom], glyph_data, args, LANG.code)
        != committed.get(atom, {}).get("strokes")
    ]
    assert mismatched == [], (
        "Hindi strokes changed. If no code changed, a dependency bump (numpy, scipy, svgpathtools) "
        "may have shifted a digit; otherwise shared code now alters Hindi."
    )


def test_marks_table_reproduces_committed(glyph_data: dict, font: str) -> None:
    """The mark recipes (prefix/suffix glyphs, shifts, widths) rebuild to the committed table."""
    # Only the fields the rebuild produces: the Hindi build adds more per mark.
    chars = LANG.chars()
    marks = build_glyph_data._build_marks(build_glyph_data._composable_marks(LANG, chars), font)
    committed = {m: {k: glyph_data["marks"][m][k] for k in entry} for m, entry in marks.items()}
    assert marks == committed
