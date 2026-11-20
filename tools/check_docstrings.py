#!/usr/bin/env python3
"""Check this project's docstring rule, which ruff and interrogate cannot enforce.

The rule (CONTRIBUTING.md, "Docstrings"):

* a **private** function (leading underscore) has a **single-line** docstring and nothing else -
  anything longer belongs in a comment, which explains *why*;
* a **public** function has a one-line summary, then NumPy ``Parameters`` and ``Returns`` sections
  (``Parameters`` only if it takes arguments, ``Returns`` only if it returns a value), even when
  they feel obvious from the signature.

ruff's ``D`` rules catch a *missing* docstring and basic format; interrogate measures coverage.
Neither notices a private helper that grew a full Parameters block, or a public function with only
a one-liner. This does. Dunder methods, nested functions and tests are out of scope.

Usage: ``python3 tools/check_docstrings.py [paths...]`` (default: python/src and tools). Exits 1
and lists every violation. Stdlib only, so the pre-commit hook can run it with bare ``python3``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = [ROOT / "python" / "src", ROOT / "tools"]


def _returns_a_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function is annotated to return something other than None."""
    returns = node.returns
    return returns is not None and not (isinstance(returns, ast.Constant) and returns.value is None)


def _takes_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function takes anything besides self or cls."""
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    names = [a.arg for a in args if a.arg not in ("self", "cls")]
    return bool(names or node.args.vararg or node.args.kwarg)


def check_source(source: str) -> list[tuple[int, str, str]]:
    """Return ``(line, function name, problem)`` for each docstring-rule violation in `source`."""
    problems = []
    tree = ast.parse(source)
    # Only module-level functions and methods of module-level classes: nested helpers are private.
    scopes: list[ast.AST] = [tree]
    scopes += [n for n in tree.body if isinstance(n, ast.ClassDef)]
    for scope in scopes:
        for node in scope.body:  # type: ignore[attr-defined]
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            name = node.name
            doc = ast.get_docstring(node)
            if doc is None or (name.startswith("__") and name.endswith("__")):
                continue
            if name.startswith("_"):
                if "\n" in doc.strip():
                    problems.append((node.lineno, name, "private: docstring must be one line"))
                continue
            if _takes_arguments(node) and "Parameters\n" not in doc:
                problems.append((node.lineno, name, "public: missing a Parameters section"))
            if _returns_a_value(node) and "Returns\n" not in doc:
                problems.append((node.lineno, name, "public: missing a Returns section"))
    return problems


def main() -> int:
    """Check the given paths (or the defaults) and return the process exit code."""
    paths = [Path(a) for a in sys.argv[1:]] or DEFAULT_PATHS
    files = sorted(f for p in paths for f in ([p] if p.is_file() else p.rglob("*.py")))
    total = 0
    for f in files:
        for line, name, problem in check_source(f.read_text(encoding="utf-8")):
            print(f"{f.relative_to(ROOT) if f.is_relative_to(ROOT) else f}:{line}: {name}: {problem}")
            total += 1
    if total:
        print(f"\n{total} docstring-rule violation(s) - see CONTRIBUTING.md, 'Docstrings'.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
