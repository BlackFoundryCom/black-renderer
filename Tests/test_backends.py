import pathlib
import pytest
from blackrenderer.colrFont import COLRFont
from blackrenderer.backendCairo import CairoPixelSurface
from blackrenderer.backendSkia import SkiaPixelSurface
from blackrenderer.backendSVG import SVGSurface

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
    ("svg", SVGSurface),
]


@pytest.mark.parametrize("glyphName", ["uni2693", "uni2694", "u1F30A", "u1F943"])
@pytest.mark.parametrize("backendName, surfaceFactory", backends)
def test_renderGlyph(backendName, surfaceFactory, glyphName):
    font = COLRFont(testFont1)

    minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

    surface = surfaceFactory(minX, minY, maxX - minX, maxY - minY)
    ext = surface.fileExtension
    font.drawGlyph(glyphName, surface.backend)

    surface.saveImage(tmpOutputDir / f"{backendName}_{glyphName}{ext}")
