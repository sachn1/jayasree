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


class TestModulesAndClasses:
    """A module and a class get a one-line docstring."""

    def test_a_multi_line_module_docstring_is_a_violation(self) -> None:
        """Ensure that a module docstring longer than one line is reported."""
        assert _problems('"""Summary.\n\nMore detail.\n"""\n') == [
            "module: docstring must be one line"
        ]

    def test_a_one_line_module_docstring_passes(self) -> None:
        """Ensure that a one-line module docstring passes."""
        assert _problems('"""Summary."""\n') == []

    def test_a_multi_line_class_docstring_is_a_violation(self) -> None:
        """Ensure that a class docstring longer than one line is reported, nested classes too."""
        src = 'class A:\n    class B:\n        """Summary.\n\n        More.\n        """\n'
        assert _problems(src) == ["class: docstring must be one line"]

    def test_a_class_defined_inside_a_function_is_also_checked(self) -> None:
        """Ensure that a class nested in a function is checked (safer than exempting it)."""
        src = (
            'def _f() -> None:\n    """F."""\n\n'
            '    class C:\n        """A.\n\n        B.\n        """\n'
        )
        assert _problems(src) == ["class: docstring must be one line"]

    def test_a_one_line_class_docstring_passes(self) -> None:
        """Ensure that a one-line class docstring passes."""
        assert _problems('class A:\n    """Summary."""\n') == []


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


class TestEdgeCases:
    """Things a naive substring check would get wrong."""

    def test_prose_mentioning_the_section_name_does_not_count_as_the_section(self) -> None:
        """Ensure that the word Parameters at a line end, without an underline, is not a section."""
        src = (
            'def f(a: int) -> None:\n    """Do it.\n\n'
            '    Mention the Parameters\n    here.\n    """\n'
        )
        assert _problems(src) == ["public: missing a Parameters section"]

    def test_a_generator_documents_yields_not_returns(self) -> None:
        """Ensure that a generator needs Yields and is satisfied by it."""
        body = "    for i in range(n):\n        yield i\n"
        missing = f'def g(n: int) -> Iterator[int]:\n    """Count."""\n{body}'
        assert "public: missing a Yields section" in _problems(missing)
        ok = (
            'def g(n: int) -> Iterator[int]:\n    """Count.\n\n    Parameters\n    ----------\n'
            "    n : int\n        How many.\n\n"
            '    Yields\n    ------\n    int\n        Each.\n    """\n' + body
        )
        assert _problems(ok) == []

    @pytest.mark.parametrize("annotation", ["NoReturn", "typing.Never", '"None"', "None"])
    def test_functions_that_return_nothing_need_no_returns_section(self, annotation: str) -> None:
        """Ensure that None, NoReturn and Never are not values to document."""
        assert _problems(f'def f() -> {annotation}:\n    """Stop."""\n') == []

    def test_methods_of_nested_classes_and_conditional_functions_are_checked(self) -> None:
        """Ensure that functions under a nested class or an if block are not skipped."""
        nested = (
            'class A:\n    class B:\n        def f(self, a: int) -> int:\n            """X."""\n'
        )
        conditional = 'if True:\n    def g(a: int) -> int:\n        """X."""\n'
        assert len(_problems(nested)) == 2
        assert len(_problems(conditional)) == 2

    def test_async_functions_follow_the_same_rule(self) -> None:
        """Ensure that an async public function needs the sections too."""
        assert len(_problems('async def f(a: int) -> int:\n    """X."""\n')) == 2

    def test_public_methods_of_a_private_class_are_checked_as_public(self) -> None:
        """Ensure that the class's privacy does not exempt its public-named methods."""
        src = 'class _A:\n    def f(self, a: int) -> None:\n        """X."""\n'
        assert _problems(src) == ["public: missing a Parameters section"]


class TestCommandLine:
    """main(): exit code and output."""

    def test_exit_code_and_listing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Ensure that a violating file exits 1 and is listed, and a clean one exits 0."""
        bad = tmp_path / "bad.py"
        bad.write_text('def f(a: int) -> int:\n    """X."""\n', encoding="utf-8")
        good = tmp_path / "good.py"
        good.write_text(PUBLIC_OK, encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["check_docstrings.py", str(bad)])
        assert check_docstrings.main() == 1
        assert "bad.py:1: f: public: missing a Parameters section" in capsys.readouterr().out
        monkeypatch.setattr(sys, "argv", ["check_docstrings.py", str(good)])
        assert check_docstrings.main() == 0


def test_the_repository_itself_follows_the_rule() -> None:
    """Ensure that python/src and tools have no docstring-rule violations."""
    problems = []
    for root in check_docstrings.DEFAULT_PATHS:
        for f in sorted(root.rglob("*.py")):
            problems += [(f.name, *p) for p in check_docstrings.check_source(f.read_text("utf-8"))]
    assert problems == []
