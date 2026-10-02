"""Tests for jayasree.languages - the language/script registry (Phase 0 of
docs/LANGUAGE_ONBOARDING_AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jayasree import languages
from jayasree.languages import (
    LANGUAGES,
    char_tuple,
    data_paths,
    get_language,
    load_build_extension,
)


class TestGetLanguage:
    """get_language: registry lookup by name."""

    def test_returns_the_registered_spec(self) -> None:
        """Ensure that a known language returns its LanguageSpec."""
        lang = get_language("malayalam")
        assert lang.code == "ml"
        assert lang.name == "Malayalam"

    def test_unknown_language_raises_with_available_list(self) -> None:
        """Ensure that an unknown language raises, listing what is registered."""
        with pytest.raises(ValueError, match="malayalam"):
            get_language("tamil")


class TestCharTuple:
    """char_tuple: optional-category access on a language's chars module."""

    def test_present_attribute_is_returned(self) -> None:
        """Ensure that an existing tuple attribute comes through unchanged."""
        chars = get_language("malayalam").chars()
        assert char_tuple(chars, "CONSONANTS") == chars.CONSONANTS
        assert char_tuple(chars, "RARE_VOWELS") == chars.RARE_VOWELS

    def test_absent_attribute_falls_back_to_empty_tuple(self) -> None:
        """Ensure that a category the module doesn't define degrades to ()."""
        chars = get_language("malayalam").chars()
        assert char_tuple(chars, "NO_SUCH_CATEGORY") == ()


class TestDataPaths:
    """data_paths: per-language committed data-file paths."""

    def test_primary_language_keeps_unsuffixed_names(self) -> None:
        """Ensure that Malayalam's files have no language suffix (backward compatibility)."""
        paths = data_paths(get_language("malayalam"))
        assert paths.glyph_data.name == "glyph-data.json"
        assert paths.stroke_data_raw.name == "stroke-data.raw.json"
        assert paths.stroke_data.name == "stroke-data.json"
        assert paths.snapshot.name == "stroke_data_raw_snapshot.json"

    def test_non_primary_language_gets_a_code_suffix(self) -> None:
        """Ensure that a hypothetical second language's files are suffixed by its code."""
        fake = languages.LanguageSpec(
            code="ta",
            name="Tamil",
            chars_module="jayasree._chars",  # reuse Malayalam's module - just testing paths
            carrier_consonant="க",
        )
        paths = data_paths(fake)
        assert paths.glyph_data.name == "glyph-data.ta.json"
        assert paths.stroke_data_raw.name == "stroke-data.ta.raw.json"
        assert paths.stroke_data.name == "stroke-data.ta.json"
        assert paths.snapshot.name == "stroke_data_raw_snapshot.ta.json"

    def test_non_primary_language_honors_data_root_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ensure a non-primary language resolves under $JAYASREE_DATA_ROOT if set."""
        monkeypatch.setenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, str(tmp_path))
        fake = languages.LanguageSpec(
            code="ta",
            name="Tamil",
            chars_module="jayasree._chars",
            carrier_consonant="க",
        )
        paths = data_paths(fake)
        assert paths.glyph_data == tmp_path / "js" / "src" / "glyph-data.ta.json"
        assert paths.snapshot == (
            tmp_path / "python" / "tests" / "snapshots" / "stroke_data_raw_snapshot.ta.json"
        )

    def test_primary_language_ignores_data_root_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ensure Malayalam's files always stay under this repo's own ROOT."""
        monkeypatch.setenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, str(tmp_path))
        paths = data_paths(get_language("malayalam"))
        assert paths.glyph_data == languages.ROOT / "js" / "src" / "glyph-data.json"


class TestLoadBuildExtension:
    """load_build_extension: optional private per-language build-time module."""

    def test_returns_none_when_env_var_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure no extension is loaded if $JAYASREE_DATA_ROOT isn't set."""
        monkeypatch.delenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, raising=False)
        assert load_build_extension("hi") is None

    def test_returns_none_when_extension_file_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ensure a configured root with no matching file degrades to None."""
        monkeypatch.setenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, str(tmp_path))
        assert load_build_extension("hi") is None

    def test_loads_matching_extension_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ensure a present build_ext_<code>.py is imported and usable."""
        monkeypatch.setenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, str(tmp_path))
        (tmp_path / "build_ext_hi.py").write_text("def recorder_note():\n    return 'test note'\n")
        ext = load_build_extension("hi")
        assert ext is not None
        assert ext.recorder_note() == "test note"

    def test_only_loads_the_requested_language_code(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ensure one language's extension file doesn't leak to another's code."""
        monkeypatch.setenv(languages.DATA_ROOT_OVERRIDE_ENV_VAR, str(tmp_path))
        (tmp_path / "build_ext_hi.py").write_text("x = 1\n")
        assert load_build_extension("ta") is None


def test_registry_entries_have_importable_chars_modules() -> None:
    """Ensure that every registered language's chars_module actually imports.

    A stale/typo'd module path here would otherwise only surface the first
    time a build tool tried to use that language.
    """
    for lang in LANGUAGES.values():
        lang.chars()  # raises ImportError if the module path is wrong
