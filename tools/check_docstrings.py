#!/usr/bin/env python3
"""Check this project's docstring rule, which ruff and interrogate cannot enforce."""
# The rule (CONTRIBUTING.md, "Docstrings"):
#
# * a **module**, a **class** and a **private** function (leading underscore) have a
#   **single-line** docstring and nothing else - anything longer belongs in a comment, which
#   explains *why*, or in `docs/`;
# * a **public** function has a one-line summary, then NumPy ``Parameters`` and ``Returns``
#   sections (``Parameters`` only if it takes arguments, ``Returns`` - or ``Yields`` for a
#   generator - only if it returns a value), even when they feel obvious from the signature.
#
# ruff's ``D`` rules catch a *missing* docstring and basic format; interrogate measures
# coverage. Neither notices a private helper that grew a full Parameters block, or a public
# function with only a one-liner. This does. Dunder methods, nested functions and tests are out
# of scope.
#
# Usage: ``python3 tools/check_docstrings.py [paths...]`` (default: python/src and tools). Exits
# 1 and lists every violation. Stdlib only, so the pre-commit hook can run it with bare
# ``python3``.

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = [ROOT / "python" / "src", ROOT / "tools"]


def _returns_a_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function is annotated to return something other than None or NoReturn."""
    returns = node.returns
    if returns is None:
        return False
    if isinstance(returns, ast.Constant):
        return returns.value not in (None, "None")
    name = returns.id if isinstance(returns, ast.Name) else getattr(returns, "attr", "")
    return name not in ("NoReturn", "Never")


def _takes_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function takes anything besides self or cls."""
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    names = [a.arg for a in args if a.arg not in ("self", "cls")]
    return bool(names or node.args.vararg or node.args.kwarg)


def _is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function itself (not a nested one) contains a yield."""
    stack = list(node.body)
    while stack:
        child = stack.pop()
        if isinstance(child, ast.Yield | ast.YieldFrom):
            return True
        if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            stack.extend(ast.iter_child_nodes(child))
    return False


def _has_section(doc: str, title: str) -> bool:
    """Whether `doc` has a real NumPy section: the title on its own line, underlined."""
    return re.search(rf"^{title}\n-{{3,}}\s*$", doc, re.MULTILINE) is not None


def _functions(body: list[ast.stmt]) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield module-level functions and methods, including nested classes and `if`/`try` bodies."""
    # A function nested inside another function is a private helper and is deliberately not yielded.
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node
        elif isinstance(node, ast.ClassDef):
            yield from _functions(node.body)
        elif isinstance(node, ast.If | ast.For | ast.While | ast.With | ast.Try):
            for field in ("body", "orelse", "finalbody"):
                yield from _functions(getattr(node, field, []))
            for handler in getattr(node, "handlers", []):
                yield from _functions(handler.body)


def check_source(source: str) -> list[tuple[int, str, str]]:
    """Return ``(line, function name, problem)`` for each docstring-rule violation in `source`.

    Parameters
    ----------
    source : str
        Python source text.

    Returns
    -------
    list[tuple[int, str, str]]
        One entry per violation, in source order within each scope.
    """
    problems = []
    tree = ast.parse(source)
    module_doc = ast.get_docstring(tree)
    if module_doc is not None and "\n" in module_doc.strip():
        problems.append((1, "<module>", "module: docstring must be one line"))
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        class_doc = ast.get_docstring(cls)
        if class_doc is not None and "\n" in class_doc.strip():
            problems.append((cls.lineno, cls.name, "class: docstring must be one line"))
    for node in _functions(tree.body):
        name = node.name
        doc = ast.get_docstring(node)
        if doc is None or (name.startswith("__") and name.endswith("__")):
            continue
        if name.startswith("_"):
            if "\n" in doc.strip():
                problems.append((node.lineno, name, "private: docstring must be one line"))
            continue
        if _takes_arguments(node) and not _has_section(doc, "Parameters"):
            problems.append((node.lineno, name, "public: missing a Parameters section"))
        if _returns_a_value(node):
            section = "Yields" if _is_generator(node) else "Returns"
            if not _has_section(doc, section):
                problems.append((node.lineno, name, f"public: missing a {section} section"))
    return problems


def main() -> int:
    """Check the given paths (or the defaults) and return the process exit code.

    Returns
    -------
    int
        0 if there are no violations, else 1.
    """
    paths = [Path(a) for a in sys.argv[1:]] or DEFAULT_PATHS
    files = sorted(f for p in paths for f in ([p] if p.is_file() else p.rglob("*.py")))
    total = 0
    for f in files:
        for line, name, problem in check_source(f.read_text(encoding="utf-8")):
            print(
                f"{f.relative_to(ROOT) if f.is_relative_to(ROOT) else f}:{line}: {name}: {problem}"
            )
            total += 1
    if total:
        print(f"\n{total} docstring-rule violation(s) - see CONTRIBUTING.md, 'Docstrings'.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
