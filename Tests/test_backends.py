import pathlib
import pytest
from fontTools.ttLib.tables.otTables import ExtendMode
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


test_colorStops = [
    (0, 1),
    (0.25, 0.75),
    (0.25, 1.5),
    (-0.5, 0.75),
]


@pytest.mark.parametrize("stopOffsets", test_colorStops)
@pytest.mark.parametrize("extend", [ExtendMode.PAD, ExtendMode.REPEAT, ExtendMode.REFLECT])
@pytest.mark.parametrize("backendName, surfaceFactory", backends)
def test_colorStops(backendName, surfaceFactory, stopOffsets, extend):
    surface = surfaceFactory(0, 0, 600, 100)
    backend = surface.backend
    rectPath = backend.newPath()
    drawRect(rectPath, 0, 0, 600, 100)
    point1 = (200, 0)
    point2 = (400, 0)
    color1 = (1, 0, 0, 1)
    color2 = (0, 0, 1, 1)
    stop1, stop2 = stopOffsets
    colorLine = [(stop1, color1), (stop2, color2)]
    with backend.savedState():
        backend.clipPath(rectPath)
        backend.fillLinearGradient(colorLine, point1, point2, extend)

    for pos in [200, 400]:
        rectPath = backend.newPath()
        drawRect(rectPath, pos, 0, 1, 100)
        with backend.savedState():
            backend.clipPath(rectPath)
            backend.fillSolid((0, 0, 0, 1))

    ext = surface.fileExtension
    stopsString = "_".join(str(s) for s in stopOffsets)
    surface.saveImage(tmpOutputDir / f"colorStops_{extend.name}_{stopsString}_{backendName}{ext}")


def drawRect(path, x, y, w, h):
    path.moveTo((x, y))
    path.lineTo((x, y + h))
    path.lineTo((x + w, y + h))
    path.lineTo((x + w, y))
    path.closePath()
