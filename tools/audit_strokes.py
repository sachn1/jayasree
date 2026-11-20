#!/usr/bin/env python3
r"""Rank a language's shipped strokes by how likely the cleanup introduced a kink.

Compares ``stroke-data.<code>.raw.json`` (the recordings) with ``stroke-data.<code>.json`` (what
ships) and prints the strokes whose sharpest bend exceeds the human's by the most - the ones to
look at first. A ranking, not a verdict; see ``jayasree.cleanup.audit``.

Usage (from the repo root, inside the Poetry environment)::

    cd python && poetry run python ../tools/audit_strokes.py --lang hindi \\
        [--top 30] [--out rows.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

from jayasree.cleanup.audit import KINK_EXCESS_DEG, audit_atoms
from jayasree.languages import data_paths, get_language


def main() -> None:
    """Audit one language's committed strokes and print the worst."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lang", default="hindi", help="Registry key (default: hindi).")
    parser.add_argument("--top", type=int, default=30, help="How many worst strokes to list.")
    parser.add_argument("--out", type=Path, help="Write every row to this JSON file.")
    args = parser.parse_args()

    paths = data_paths(get_language(args.lang))
    raw = json.loads(paths.stroke_data_raw.read_text(encoding="utf-8"))
    processed = json.loads(paths.stroke_data.read_text(encoding="utf-8"))
    rows = audit_atoms(raw, processed)
    measured = [r for r in rows if "excess" in r]
    flagged = [r for r in measured if r["excess"] > KINK_EXCESS_DEG]
    print(
        f"{len(measured)} strokes audited; {len(flagged)} with a sharper bend than the recording "
        f"(> {KINK_EXCESS_DEG:.0f} deg more)."
    )
    columns = ("stk", "same", "human", "clean", "excess", "flips", "dev")
    print(f"{'atom':8s} " + " ".join(f"{c:>6s}" for c in columns))
    for r in measured[: args.top]:
        print(
            f"{r['atom']:8s} {r['stroke']:>6d} {'yes' if r['unchanged'] else '':>6s} "
            f"{r['bend_human']:>6.0f} {r['bend_cleaned']:>6.0f} {r['excess']:>6.0f} "
            f"{r['flips']:>6d} {r['max_dev_fu']:>6.0f}"
        )
    for r in rows:
        if "stroke_count_mismatch" in r:
            counts = r["stroke_count_mismatch"]
            print(f"  note: {r['atom']!r} has {counts} strokes (recorded, shipped)")
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
