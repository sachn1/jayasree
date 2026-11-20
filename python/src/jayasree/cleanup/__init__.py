"""Stroke cleanup: replace a hand-recorded stroke's wobble with the font's own geometry.

Run per language, and only for Hindi so far (the language is the switch); see :mod:`jayasree.cleanup.stroke` for
the method and ``docs/ARCHITECTURE.md`` ("Cleanup") for where it sits in the pipeline.
"""

from jayasree.cleanup.stroke import clean_stroke, clean_strokes

__all__ = ["clean_stroke", "clean_strokes"]
