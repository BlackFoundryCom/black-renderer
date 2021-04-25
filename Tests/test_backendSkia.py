import pathlib
import pytest
from blackrenderer.colrFont import COLRFont
from blackrenderer.backendSkia import SkiaBackend, SkiaPixelSurface


testDir = pathlib.Path(__file__).resolve().parent
dataDir = testDir / "data"
tmpOutputDir = testDir / "tmpOutput"
if not tmpOutputDir.exists():
    tmpOutputDir.mkdir()


testFont1 = dataDir / "noto-glyf_colr_1.ttf"
testFont2 = dataDir / "samples-glyf_colr_1.ttf"


@pytest.mark.parametrize("glyphName", ["uni2693", "uni2694"])
def test_renderGlyph(glyphName):
    font = COLRFont(testFont1)

    minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

    surface = SkiaPixelSurface(minX, minY, maxX - minX, maxY - minY)
    backend = SkiaBackend(surface.canvas)

    font.drawGlyph(glyphName, backend)

    surface.saveImage(tmpOutputDir / f"skia_{glyphName}.png")
