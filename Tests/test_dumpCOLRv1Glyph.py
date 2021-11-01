import pathlib
from blackrenderer.font import BlackRendererFont
from blackrenderer.dumpCOLRv1Glyph import dumpCOLRv1Glyph


testDir = pathlib.Path(__file__).resolve().parent
testFont1 = testDir / "data" / "noto-glyf_colr_1.ttf"


expected_output = """\
uni2693
  # PaintColrLayers
  Layers
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 2148
          Alpha 1.0
      Glyph glyph39143
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 871
          Alpha 1.0
      Glyph glyph39144
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 2491
          Alpha 1.0
      Glyph glyph39145
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 871
          Alpha 0.89
      Glyph glyph39146
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 2491
          Alpha 1.0
      Glyph glyph39147
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          PaletteIndex 871
          Alpha 1.0
      Glyph glyph39148
"""


def test_dump(capsys):
    font = BlackRendererFont(testFont1)
    dumpCOLRv1Glyph(font, "uni2693")
    captured = capsys.readouterr()
    assert expected_output == captured.out
