# Malayalam font strokes

For contributors regenerating the font-based Malayalam strokes: the pen strokes in the sources of three SMC
fonts (Chilanka, Manjari, Nupuram), chosen per letter, as a second stroke set beside the recorded handwriting.
The licence is the fonts' OFL, not CC BY-SA; see [`LICENSE-DATA`](../../../LICENSE-DATA) and `third-party/`.

1. **Extract.** `tools/build_font_strokes.py extract --chilanka DIR --manjari DIR [--nupuram DIR]` reads the
   designers' strokes from clones of the font repositories (Nupuram from its MetaPost glyph sources, built with
   its own Makefile) into `js/src/font-strokes.ml.json`.
2. **Stitch.** `tools/stitch_font_strokes.py` adds a "Stitched" option for a letter the fonts lack, built from
   the strokes already chosen for its parts. Run it after `extract`, and again after the choices change.
3. **Choose.** `tools/font-stroke-chooser.html` shows every stroke of every font as its own card. Pick the
   strokes that make up each letter and export the choices to `tools/font-stroke-choices.ml.json`.
4. **Build.** `tools/build_font_strokes.py build` writes `js/src/stroke-data.font.json`, which a writer loads
   with `loadStrokes()`. A letter taken entirely from Chilanka is stretched sideways to the width of its
   Manjari letter, so spacing is the same whichever font a letter came from.

Nothing from the handwriting set may appear in font mode: the writer is created with `outlineFallback: false`,
and `python/tests/test_font_strokes.py` checks that no font cluster shares a stroke path with the handwriting.
