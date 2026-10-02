"""Tests for jayasree._chars_hi - the Hindi (Devanagari) Unicode character inventory.

Explicitly Hindi-specific (unlike test_geometry.py/test_centering.py/
test_ghost_reference.py/test_stroke_compose.py, which test the
script-agnostic engine) - its own file per test_chars_malayalam.py's own
docstring instruction ("A future script's own character inventory should
get its own test_chars_<script>.py file rather than touching this one").
"""

from __future__ import annotations

from jayasree import _chars_hi

# Devanagari Unicode block, per the Unicode Standard.
DEVANAGARI_BLOCK = range(0x0900, 0x0980)

TUPLE_CONSTANTS = [
    "CORE_INDEPENDENT_VOWELS",
    "LOAN_VOWELS",
    "INDEPENDENT_VOWELS",
    "RARE_VOWELS",
    "STANDARD_CONSONANTS",
    "NUKTA_CONSONANTS",
    "CONSONANTS",
    "CORE_MATRAS",
    "LOAN_MATRAS",
    "MATRAS",
    "RARE_MATRAS",
    "NUMERALS",
    "NATIVE_PUNCTUATION",
    "RARE_MARKS",
]

#: Categories meant to be pairwise disjoint from each other - excludes the
#: composed unions (INDEPENDENT_VOWELS, CONSONANTS, MATRAS), which overlap
#: their own constituent categories by construction, not by mistake.
DISJOINT_TUPLE_CONSTANTS = [
    "CORE_INDEPENDENT_VOWELS",
    "LOAN_VOWELS",
    "RARE_VOWELS",
    "STANDARD_CONSONANTS",
    "NUKTA_CONSONANTS",
    "CORE_MATRAS",
    "LOAN_MATRAS",
    "RARE_MATRAS",
    "NUMERALS",
    "NATIVE_PUNCTUATION",
    "RARE_MARKS",
]

SCALAR_CONSTANTS = ["VIRAMA", "ANUSVARA", "CANDRABINDU", "VISARGA", "NUKTA"]


class TestExpectedCounts:
    """Each category has the specific count documented in its own comment."""

    def test_core_independent_vowels_count(self) -> None:
        """Ensure that there are exactly 11 core independent vowels."""
        assert len(_chars_hi.CORE_INDEPENDENT_VOWELS) == 11

    def test_loan_vowels_count(self) -> None:
        """Ensure that there are exactly 2 loan-vowel letters."""
        assert len(_chars_hi.LOAN_VOWELS) == 2

    def test_independent_vowels_is_core_plus_loan(self) -> None:
        """Ensure that INDEPENDENT_VOWELS is exactly CORE_INDEPENDENT_VOWELS + LOAN_VOWELS."""
        core, loan = _chars_hi.CORE_INDEPENDENT_VOWELS, _chars_hi.LOAN_VOWELS
        assert _chars_hi.INDEPENDENT_VOWELS == core + loan
        assert len(_chars_hi.INDEPENDENT_VOWELS) == 13

    def test_rare_vowels_count(self) -> None:
        """Ensure that there are exactly 3 rare independent vowels."""
        assert len(_chars_hi.RARE_VOWELS) == 3

    def test_standard_consonants_count(self) -> None:
        """Ensure that there are exactly 33 standard consonants."""
        assert len(_chars_hi.STANDARD_CONSONANTS) == 33

    def test_nukta_consonants_count(self) -> None:
        """Ensure that there are exactly 7 nukta-modified consonants."""
        assert len(_chars_hi.NUKTA_CONSONANTS) == 7

    def test_consonants_is_standard_plus_nukta(self) -> None:
        """Ensure that CONSONANTS is exactly STANDARD_CONSONANTS + NUKTA_CONSONANTS."""
        assert _chars_hi.CONSONANTS == _chars_hi.STANDARD_CONSONANTS + _chars_hi.NUKTA_CONSONANTS
        assert len(_chars_hi.CONSONANTS) == 40

    def test_core_matras_count(self) -> None:
        """Ensure that there are exactly 10 core dependent vowel signs."""
        assert len(_chars_hi.CORE_MATRAS) == 10

    def test_loan_matras_count(self) -> None:
        """Ensure that there are exactly 2 loan matra signs."""
        assert len(_chars_hi.LOAN_MATRAS) == 2

    def test_matras_is_core_plus_loan(self) -> None:
        """Ensure that MATRAS is exactly CORE_MATRAS + LOAN_MATRAS."""
        assert _chars_hi.MATRAS == _chars_hi.CORE_MATRAS + _chars_hi.LOAN_MATRAS
        assert len(_chars_hi.MATRAS) == 12

    def test_rare_matras_count(self) -> None:
        """Ensure that there are exactly 3 rare matra signs."""
        assert len(_chars_hi.RARE_MATRAS) == 3

    def test_numerals_count(self) -> None:
        """Ensure that there are exactly 10 Devanagari digits."""
        assert len(_chars_hi.NUMERALS) == 10

    def test_native_punctuation_count(self) -> None:
        """Ensure that there are exactly 2 native punctuation marks (danda/double danda)."""
        assert len(_chars_hi.NATIVE_PUNCTUATION) == 2

    def test_rare_marks_count(self) -> None:
        """Ensure that there are exactly 2 rare marks (avagraha/Om)."""
        assert len(_chars_hi.RARE_MARKS) == 2


class TestNoDuplicates:
    """No category contains the same character twice."""

    def test_each_tuple_constant_has_unique_characters(self) -> None:
        """Ensure that every tuple constant contains only distinct characters."""
        for name in TUPLE_CONSTANTS:
            value = getattr(_chars_hi, name)
            assert len(value) == len(set(value)), f"{name} has duplicate characters"


class TestNoOverlapBetweenCategories:
    """No character belongs to two different leaf categories."""

    def test_categories_are_pairwise_disjoint(self) -> None:
        """Ensure that no character appears in more than one distinct leaf category."""
        categories = {name: set(getattr(_chars_hi, name)) for name in DISJOINT_TUPLE_CONSTANTS}
        names = list(categories)
        for i, name_a in enumerate(names):
            for name_b in names[i + 1 :]:
                overlap = categories[name_a] & categories[name_b]
                assert not overlap, f"{name_a} and {name_b} overlap: {overlap}"


class TestAllCharactersAreInTheDevanagariBlock:
    """Every character constant falls within U+0900-U+097F."""

    def test_tuple_constants(self) -> None:
        """Ensure that every character in every tuple constant is in the Devanagari block."""
        for name in TUPLE_CONSTANTS:
            for ch in getattr(_chars_hi, name):
                assert ord(ch) in DEVANAGARI_BLOCK, f"{name} contains {ch!r} outside the block"

    def test_scalar_constants(self) -> None:
        """Ensure that every scalar (single-character) constant is in the Devanagari block."""
        for name in SCALAR_CONSTANTS:
            ch = getattr(_chars_hi, name)
            assert ord(ch) in DEVANAGARI_BLOCK, f"{name} ({ch!r}) is outside the block"


class TestNuktaConsonantsHaveCanonicalDecomposition:
    """Regression coverage for build_glyph_data.py's _HI_NUKTA_CONSONANTS table.

    Each of the 7 precomposed nukta consonants must have a real Unicode
    canonical NFD decomposition into base-consonant + U+093C (verified
    while building that table - see its own docstring) - if a future
    Unicode/font update ever broke that assumption, `legacyEncodings`
    normalization would silently stop covering the decomposed spelling.
    """

    def test_each_nukta_consonant_decomposes_to_base_plus_nukta(self) -> None:
        """Ensure that every nukta consonant's NFD decomposition is base + NUKTA."""
        import unicodedata

        for ch in _chars_hi.NUKTA_CONSONANTS:
            decomposition = unicodedata.normalize("NFD", ch)
            assert len(decomposition) == 2, f"{ch!r} did not decompose into 2 characters"
            combining_mark = decomposition[1]
            assert combining_mark == _chars_hi.NUKTA, f"{ch!r} did not decompose with NUKTA"


class TestPublicApi:
    """__all__ matches exactly what's importable, with no accidental omissions."""

    def test_all_matches_module_exports(self) -> None:
        """Ensure that __all__ lists exactly the tuple and scalar constants."""
        expected = set(TUPLE_CONSTANTS) | set(SCALAR_CONSTANTS)
        assert set(_chars_hi.__all__) == expected
