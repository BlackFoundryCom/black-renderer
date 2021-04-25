import pathlib
import pytest
from blackrenderer.colrFont import COLRFont
from blackrenderer.backendCairo import CairoPixelSurface
from blackrenderer.backendSkia import SkiaPixelSurface


testDir = pathlib.Path(__file__).resolve().parent
dataDir = testDir / "data"
tmpOutputDir = testDir / "tmpOutput"
if not tmpOutputDir.exists():
    tmpOutputDir.mkdir()


testFont1 = dataDir / "noto-glyf_colr_1.ttf"
testFont2 = dataDir / "samples-glyf_colr_1.ttf"


backends = [
    ("cairo", CairoPixelSurface),
    ("skia", SkiaPixelSurface),
]


@pytest.mark.parametrize("backendName, surfaceFactory", backends)
@pytest.mark.parametrize("glyphName", ["uni2693", "uni2694"])
def test_renderGlyph(backendName, surfaceFactory, glyphName):
    font = COLRFont(testFont1)

    minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

    surface = surfaceFactory(minX, minY, maxX - minX, maxY - minY)
    font.drawGlyph(glyphName, surface.backend)

    surface.saveImage(tmpOutputDir / f"{backendName}_{glyphName}.png")
