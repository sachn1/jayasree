"""Tests for tools/check_docstrings.py - the private/public docstring rule."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

import check_docstrings

PUBLIC_OK = '''
def f(a: int, b: int) -> int:
    """Add.

    Parameters
    ----------
    a : int
        First.
    b : int
        Second.

    Returns
    -------
    int
        The sum.
    """
    return a + b
'''


def _problems(source: str) -> list[str]:
    """Return just the problem texts for `source`."""
    return [p for _, _, p in check_docstrings.check_source(source)]


class TestPrivateFunctions:
    """A private function gets a one-line docstring."""

    def test_one_line_is_fine(self) -> None:
        """Ensure that a one-line docstring on a private function passes."""
        assert _problems('def _f(a: int) -> int:\n    """Add one."""\n    return a + 1\n') == []

    def test_a_longer_docstring_is_a_violation(self) -> None:
        """Ensure that a multi-line docstring on a private function is reported."""
        src = 'def _f(a: int) -> int:\n    """Add one.\n\n    More detail.\n    """\n    return a\n'
        assert _problems(src) == ["private: docstring must be one line"]

    def test_a_private_function_needs_no_sections(self) -> None:
        """Ensure that a private function with arguments and a return is not asked for sections."""
        assert _problems('def _f(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n') == []


class TestPublicFunctions:
    """A public function gets Parameters and Returns."""

    def test_complete_docstring_passes(self) -> None:
        """Ensure that a public function with both sections passes."""
        assert _problems(PUBLIC_OK) == []

    def test_missing_parameters_and_returns_are_reported(self) -> None:
        """Ensure that a one-line public docstring is flagged for both sections."""
        src = 'def f(a: int) -> int:\n    """Add one."""\n    return a + 1\n'
        assert _problems(src) == [
            "public: missing a Parameters section",
            "public: missing a Returns section",
        ]

    def test_no_arguments_and_no_return_need_no_sections(self) -> None:
        """Ensure that a public function with nothing to document passes with a one-liner."""
        assert _problems('def f() -> None:\n    """Do it."""\n') == []

    def test_self_alone_does_not_need_parameters(self) -> None:
        """Ensure that a method taking only self is not asked for a Parameters section."""
        src = 'class C:\n    def f(self) -> None:\n        """Do it."""\n'
        assert _problems(src) == []

    def test_only_returns_missing_is_reported_alone(self) -> None:
        """Ensure that a function with Parameters but no Returns is flagged for Returns only."""
        src = (
            'def f(a: int) -> int:\n    """Add.\n\n    Parameters\n    ----------\n'
            '    a : int\n        First.\n    """\n    return a\n'
        )
        assert _problems(src) == ["public: missing a Returns section"]


class TestScope:
    """What is out of scope."""

    @pytest.mark.parametrize("name", ["__init__", "__repr__"])
    def test_dunder_methods_are_skipped(self, name: str) -> None:
        """Ensure that magic methods are not checked."""
        src = f'class C:\n    def {name}(self, a: int) -> int:\n        """Short."""\n'
        assert _problems(src) == []

    def test_nested_functions_are_skipped(self) -> None:
        """Ensure that a helper nested in a function is treated as private and not checked."""
        src = (
            'def _outer() -> None:\n    """Outer."""\n\n'
            '    def inner(a: int) -> int:\n        """Inner.\n\n        Long.\n        """\n'
            "        return a\n"
        )
        assert _problems(src) == []

    def test_a_function_without_a_docstring_is_left_to_ruff(self) -> None:
        """Ensure that a missing docstring is not this tool's job."""
        assert _problems("def f(a: int) -> int:\n    return a\n") == []


def test_the_repository_itself_follows_the_rule() -> None:
    """Ensure that python/src and tools have no docstring-rule violations."""
    assert check_docstrings.main.__module__ == "check_docstrings"
    problems = []
    for root in check_docstrings.DEFAULT_PATHS:
        for f in sorted(root.rglob("*.py")):
            problems += [(f.name, *p) for p in check_docstrings.check_source(f.read_text("utf-8"))]
    assert problems == []
