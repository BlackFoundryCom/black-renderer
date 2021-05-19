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
          # PaintLinearGradient
          Format 4
          ColorLine
            - (0.014, (117, 117, 117, 255))
            - (0.172, (129, 129, 129, 255))
            - (0.459, (162, 162, 162, 255))
            - (0.84, (214, 214, 214, 255))
            - (1.0, (238, 238, 238, 255))
          x0 638
          y0 -212
          x1 638
          y1 909
          x2 1758
          y2 -212
      Glyph glyph44642
    - # PaintGlyph
      Format 10
      Paint
          # PaintSolid
          Format 2
          Color (13, 71, 161, 51)
      Glyph glyph44643
"""


def test_dump(capsys):
    font = BlackRendererFont(testFont1)
    dumpCOLRv1Glyph(font, "uni2693")
    captured = capsys.readouterr()
    assert expected_output == captured.out
