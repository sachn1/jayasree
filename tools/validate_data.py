#!/usr/bin/env python3
"""Validate the structural integrity of the committed data files.

Catches accidental corruption (malformed JSON, empty/invalid stroke paths,
missing required keys) before it's committed - run via pre-commit/CI, or:

    python tools/validate_data.py

Discovers and validates every language's data-file triple under js/src/
(Phase 0 of docs/LANGUAGE_ONBOARDING_AGENTS.md) - today, just Malayalam's.

Deliberately dependency-free (stdlib only, no `jayasree` import): the
pre-commit hook (.pre-commit-config.yaml's ``validate-data``) runs this via
``language: system`` on every commit touching a data file, using whatever
bare ``python3`` happens to be on the committer's PATH - there's no
guarantee the full `jayasree` package's dependencies (uharfbuzz, in
particular) are installed there. `--lang`'s codes are duplicated as bare
strings from `jayasree.languages.LANGUAGES` for the same reason (see
`_PRIMARY_CODE` below) - keep them in sync by hand if that registry changes.

Also owns each language's stroke-data.raw.json content-hash snapshot, used
by python/tests/test_data_snapshot.py (a *content* check, complementing this
file's *structural* one - see that test's docstring). Regenerate Malayalam's
after a deliberate, reviewed change to previously-recorded data:

    python tools/validate_data.py --update-snapshot

Pass ``--lang <code>`` (e.g. ``ta``) to target a different language's
snapshot; omit it (or pass ``ml``) for Malayalam's unsuffixed files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

#: Malayalam's code in jayasree.languages.LANGUAGES - the one language whose
#: files keep their original, unsuffixed names. See this file's module
#: docstring for why this is a duplicated literal, not an import.
_PRIMARY_CODE = "ml"

_GLYPH_DATA_RE = re.compile(r"^glyph-data(?:\.(?P<code>[a-z]+))?\.json$")


@dataclass(frozen=True)
class DataPaths:
    """One language's committed data-file paths."""

    code: str
    glyph_data: Path
    stroke_data_raw: Path
    stroke_data: Path
    snapshot: Path


def paths_for(code: str) -> DataPaths:
    """Return the committed data-file paths for language `code`.

    Parameters
    ----------
    code : str
        A language code (e.g. ``"ta"``), or `_PRIMARY_CODE`/``""`` for
        Malayalam's unsuffixed files.

    Returns
    -------
    DataPaths
    """
    code = "" if code == _PRIMARY_CODE else code
    suffix = f".{code}" if code else ""
    js_src = ROOT / "js" / "src"
    return DataPaths(
        code=code or _PRIMARY_CODE,
        glyph_data=js_src / f"glyph-data{suffix}.json",
        stroke_data_raw=js_src / f"stroke-data{suffix}.raw.json",
        stroke_data=js_src / f"stroke-data{suffix}.json",
        snapshot=ROOT / "python" / "tests" / "snapshots" / f"stroke_data_raw_snapshot{suffix}.json",
    )


def discover_languages(src_dir: Path | None = None) -> list[DataPaths]:
    """Find every language's glyph-data*.json under `src_dir` (default: js/src/).

    Parameters
    ----------
    src_dir : Path or None
        Directory to scan; defaults to the repo's `js/src/`.

    Returns
    -------
    list[DataPaths]
        One entry per matching `glyph-data*.json` found, unsuffixed
        (Malayalam) first.
    """
    src_dir = src_dir or (ROOT / "js" / "src")
    found: list[DataPaths] = []
    for path in sorted(src_dir.glob("glyph-data*.json")):
        m = _GLYPH_DATA_RE.match(path.name)
        if not m:
            continue  # e.g. a stray backup file - not a real language data file
        found.append(paths_for(m.group("code") or _PRIMARY_CODE))
    return found


# Backward-compatible aliases for Malayalam's paths - test_validate_data.py
# and anything else importing these directly keeps working unchanged.
_ML_PATHS = paths_for(_PRIMARY_CODE)
GLYPH_DATA = _ML_PATHS.glyph_data
STROKE_DATA_RAW = _ML_PATHS.stroke_data_raw
STROKE_DATA = _ML_PATHS.stroke_data
SNAPSHOT = _ML_PATHS.snapshot

_SVG_PATH_RE = re.compile(r"^M\s*-?[\d.]+\s+-?[\d.]+")

# Language-agnostic whitespace/punctuation - kept in sync by hand with
# UNIVERSAL_CHARS in js/src/index.js (the canonical definition) and its
# duplicate in tools/stroke-recorder.js (duplicated there too, deliberately
# - see that file's own comment on why a shared import isn't safe for the
# file://-opened standalone recorder). These are rendered as plain static
# text at runtime, never touch any of the three data files below, and never
# need a recorded stroke - this check makes that a CI-enforced invariant,
# not just something the recorder tool's UI happens to prevent.
_UNIVERSAL_CHARS = frozenset(" .,!?;:-'\"()")


def check_no_universal_chars(data: dict, filename: str) -> list[str]:
    """Verify no cluster key in `data` is a universal whitespace/punctuation character.

    Parameters
    ----------
    data : dict
        Parsed JSON content (glyph-data.json's ``clusters``, or a
        stroke-data(.raw).json file) to check cluster keys of.
    filename : str
        Name used in error messages (e.g. ``"stroke-data.raw.json"``).

    Returns
    -------
    list[str]
        One error message per offending cluster key found.
    """
    return [
        f"{filename}: {cluster!r} is universal whitespace/punctuation (see "
        f"UNIVERSAL_CHARS in js/src/index.js) and must never be a recorded/shaped cluster"
        for cluster in data
        if cluster in _UNIVERSAL_CHARS
    ]


def validate_stroke_d(d: Any, where: str) -> list[str]:
    """Validate one stroke's `d` value, returning a list of error messages.

    Parameters
    ----------
    d : Any
        The value to validate as an SVG path ``d`` string.
    where : str
        Human-readable location (for error messages), e.g. ``"ക.strokes[0]"``.

    Returns
    -------
    list[str]
        Error messages; empty if `d` is valid.
    """
    if not isinstance(d, str):
        return [f"{where}: 'd' is not a string ({type(d).__name__})"]
    if not d.strip():
        return [f"{where}: 'd' is empty"]
    if not _SVG_PATH_RE.match(d):
        return [f"{where}: 'd' does not start with a valid moveto command: {d[:30]!r}"]
    return []


def validate_stroke_data(data: Any, filename: str) -> list[str]:
    """Validate a stroke-data(.raw).json structure, returning error messages.

    Parameters
    ----------
    data : Any
        Parsed JSON content to validate.
    filename : str
        Name used in error messages (e.g. ``"stroke-data.raw.json"``).

    Returns
    -------
    list[str]
        Error messages; empty if the structure is fully valid.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{filename}: top level must be an object, got {type(data).__name__}"]

    for cluster, entry in data.items():
        where = f"{filename}:{cluster!r}"
        if not isinstance(entry, dict) or "strokes" not in entry:
            errors.append(f"{where}: missing 'strokes' key")
            continue
        strokes = entry["strokes"]
        if not isinstance(strokes, list):
            errors.append(f"{where}.strokes: must be a list, got {type(strokes).__name__}")
            continue
        if not strokes:
            errors.append(
                f"{where}.strokes: empty - a recorded cluster must have at least one stroke"
            )
        for i, stroke in enumerate(strokes):
            if not isinstance(stroke, dict) or "d" not in stroke:
                errors.append(f"{where}.strokes[{i}]: missing 'd' key")
                continue
            errors.extend(validate_stroke_d(stroke["d"], f"{where}.strokes[{i}]"))

    return errors


def validate_glyph_data(data: Any) -> list[str]:
    """Validate glyph-data.json's structure, returning error messages.

    Parameters
    ----------
    data : Any
        Parsed JSON content to validate.

    Returns
    -------
    list[str]
        Error messages; empty if the structure is fully valid.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["glyph-data.json: top level must be an object"]
    if "clusters" not in data:
        errors.append("glyph-data.json: missing 'clusters' key")
        return errors
    if "meta" not in data or not isinstance(data.get("meta"), dict):
        errors.append("glyph-data.json: missing or invalid 'meta' key")
    elif "unitsPerEm" not in data["meta"]:
        errors.append("glyph-data.json.meta: missing 'unitsPerEm'")

    clusters = data["clusters"]
    if not isinstance(clusters, dict) or not clusters:
        errors.append("glyph-data.json.clusters: must be a non-empty object")
        return errors

    for cluster, entry in clusters.items():
        where = f"glyph-data.json.clusters:{cluster!r}"
        if not isinstance(entry, dict) or "glyphs" not in entry:
            errors.append(f"{where}: missing 'glyphs' key")
            continue
        glyphs = entry["glyphs"]
        if not isinstance(glyphs, list) or not glyphs:
            errors.append(f"{where}.glyphs: must be a non-empty list")
            continue
        for i, glyph in enumerate(glyphs):
            if not isinstance(glyph, dict) or "d" not in glyph:
                errors.append(f"{where}.glyphs[{i}]: missing 'd' key")
                continue
            # A glyph's own outline `d` may legitimately be empty (a space
            # character has no ink) - only check well-formedness when present.
            if glyph["d"] and not _SVG_PATH_RE.match(glyph["d"]):
                errors.append(
                    f"{where}.glyphs[{i}]: 'd' does not start with a valid moveto command"
                )

    contextual_forms = data.get("contextualForms")
    if contextual_forms is not None:
        if not isinstance(contextual_forms, dict):
            errors.append("glyph-data.json.contextualForms: must be an object")
        else:
            for trigger, form in contextual_forms.items():
                where = f"glyph-data.json.contextualForms:{trigger!r}"
                if not isinstance(trigger, str) or len(trigger) != 2:
                    errors.append(f"{where}: key must be a 2-character string")
                if not isinstance(form, dict) or form.get("role") not in ("halfForm", "reph"):
                    errors.append(f"{where}: 'role' must be 'halfForm' or 'reph'")
                    continue
                ghost = form.get("ghost")
                if (
                    not isinstance(ghost, dict)
                    or not isinstance(ghost.get("glyphs"), list)
                    or not ghost["glyphs"]
                ):
                    errors.append(f"{where}.ghost: missing non-empty 'glyphs' list")

    return errors


def cross_check_raw_in_processed(raw: dict, processed: dict) -> list[str]:
    """Verify every hand-authored cluster survived into the processed file.

    Parameters
    ----------
    raw : dict
        Parsed stroke-data.raw.json content.
    processed : dict
        Parsed stroke-data.json content.

    Returns
    -------
    list[str]
        One error message per raw cluster missing from the processed file.
    """
    missing = sorted(set(raw) - set(processed))
    return [f"stroke-data.json: missing hand-authored cluster {c!r} from raw" for c in missing]


def hash_strokes(entry: dict) -> str:
    """Compute a stable content hash for one cluster's recorded strokes.

    Parameters
    ----------
    entry : dict
        A single ``stroke-data.raw.json`` value, i.e. ``{"strokes": [...]}}``.

    Returns
    -------
    str
        A short, stable hex digest of the entry's stroke path data.
    """
    d_values = [s.get("d", "") for s in entry.get("strokes", [])]
    payload = "|".join(d_values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_snapshot(raw: dict) -> dict[str, str]:
    """Build a ``{cluster: content_hash}`` snapshot from raw stroke data.

    Parameters
    ----------
    raw : dict
        Parsed ``stroke-data.raw.json`` content.

    Returns
    -------
    dict[str, str]
        Mapping of cluster key to its stroke-content hash.
    """
    return {cluster: hash_strokes(entry) for cluster, entry in raw.items()}


def update_snapshot(raw: dict, snapshot_path: Path = SNAPSHOT) -> None:
    """Regenerate a language's stroke-data.raw.json content-hash snapshot and write it.

    Parameters
    ----------
    raw : dict
        Parsed ``stroke-data.raw.json`` content.
    snapshot_path : Path
        Where to write the snapshot - defaults to Malayalam's.
    """
    snapshot = build_snapshot(raw)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {snapshot_path.relative_to(ROOT)} ({len(snapshot)} clusters).")


def _validate_language(label: str, paths: DataPaths) -> tuple[list[str], dict, dict, dict]:
    """Validate one language's data-file triple.

    Parameters
    ----------
    label : str
        Human-readable name for error messages (e.g. ``"Malayalam"``).
    paths : DataPaths
        This language's ``glyph_data``/``stroke_data_raw``/``stroke_data`` paths.

    Returns
    -------
    tuple[list[str], dict, dict, dict]
        ``(errors, glyph_data, raw, processed)`` - the three parsed
        structures are returned alongside the errors so `main()` can report
        cluster counts without re-reading the files.
    """
    errors: list[str] = []

    def _load(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: could not read/parse {path}: {exc}")
            return None

    glyph_data = _load(paths.glyph_data)
    raw = _load(paths.stroke_data_raw)
    processed = _load(paths.stroke_data)
    if glyph_data is None or raw is None or processed is None:
        return errors, glyph_data or {}, raw or {}, processed or {}

    glyph_name = paths.glyph_data.name
    raw_name = paths.stroke_data_raw.name
    processed_name = paths.stroke_data.name

    errors.extend(validate_glyph_data(glyph_data))
    errors.extend(validate_stroke_data(raw, raw_name))
    errors.extend(validate_stroke_data(processed, processed_name))
    errors.extend(check_no_universal_chars(glyph_data.get("clusters", {}), glyph_name))
    errors.extend(check_no_universal_chars(raw, raw_name))
    errors.extend(check_no_universal_chars(processed, processed_name))
    errors.extend(cross_check_raw_in_processed(raw, processed))

    return [f"{label}: {e}" for e in errors], glyph_data, raw, processed


def main() -> int:
    """Validate every onboarded language's committed data files, printing any errors.

    Also handles ``--update-snapshot --lang <code>``, which regenerates one
    language's content-hash snapshot instead of validating.

    Returns
    -------
    int
        Exit code (0 = success, 1 = validation errors found).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-snapshot",
        action="store_true",
        help="Regenerate a language's stroke-data.raw.json content-hash snapshot instead of "
        "validating.",
    )
    parser.add_argument(
        "--lang",
        default=_PRIMARY_CODE,
        help="Language code (e.g. 'ta') - only used with --update-snapshot "
        f"(default: {_PRIMARY_CODE}, Malayalam's unsuffixed files). Plain validation always "
        "checks every language found under js/src/.",
    )
    args = parser.parse_args()

    if args.update_snapshot:
        paths = paths_for(args.lang)
        try:
            raw = json.loads(paths.stroke_data_raw.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FATAL: could not read/parse {paths.stroke_data_raw}: {exc}", file=sys.stderr)
            return 1
        update_snapshot(raw, paths.snapshot)
        return 0

    onboarded = discover_languages()
    if not onboarded:
        src_dir = ROOT / "js" / "src"
        print(f"FATAL: no glyph-data*.json files found under {src_dir}.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    summary: list[str] = []
    for paths in onboarded:
        errors, glyph_data, raw, processed = _validate_language(paths.code, paths)
        all_errors.extend(errors)
        if not errors:
            summary.append(
                f"{paths.code}: {len(raw)} raw, {len(processed)} processed, "
                f"{len(glyph_data.get('clusters', {}))} glyph clusters"
            )

    if all_errors:
        print(f"Found {len(all_errors)} data integrity error(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK ({len(onboarded)} language(s)): " + "; ".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
