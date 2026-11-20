"""Stroke cleanup: replace a hand-recorded stroke's wobble with the font's own geometry.

Run per language, and only for Hindi so far (the language is the switch). See
:mod:`jayasree.cleanup.stroke` for the method, ``docs/ARCHITECTURE.md`` ("Cleanup (Hindi)") for
where it sits in the pipeline, and :mod:`jayasree.cleanup.audit` for ranking the results.
"""

from jayasree.cleanup.stroke import clean_stroke, clean_strokes

__all__ = ["clean_stroke", "clean_strokes"]
