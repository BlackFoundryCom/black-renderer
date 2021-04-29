import pathlib
import pytest
from fontTools.ttLib.tables.otTables import ExtendMode
from blackrenderer.font import BlackRendererFont
from blackrenderer.backends import getSurface


testDir = pathlib.Path(__file__).resolve().parent
dataDir = testDir / "data"
tmpOutputDir = testDir / "tmpOutput"
if not tmpOutputDir.exists():
    tmpOutputDir.mkdir()


backends = [
    (name, getSurface(name)) for name in ["cairo", "coregraphics", "skia", "svg"]
]
backends = [(name, surface) for name, surface in backends if surface is not None]


testFonts = {
    "noto": dataDir / "noto-glyf_colr_1.ttf",
    "mutator": dataDir / "MutatorSans.ttf",
}


test_glyphs = [
    ("noto", "uni2693"),
    ("noto", "uni2694"),
    ("noto", "u1F30A"),
    ("noto", "u1F943"),
    ("mutator", "B"),
]


@pytest.mark.parametrize("fontName, glyphName", test_glyphs)
@pytest.mark.parametrize("backendName, surfaceFactory", backends)
def test_renderGlyph(backendName, surfaceFactory, fontName, glyphName):
    font = BlackRendererFont(testFonts[fontName])

    minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

    surface = surfaceFactory(minX, minY, maxX - minX, maxY - minY)
    ext = surface.fileExtension
    font.drawGlyph(glyphName, surface.canvas)

    surface.saveImage(tmpOutputDir / f"glyph_{fontName}_{glyphName}_{backendName}{ext}")


test_colorStops = [
    (0, 1),
]

test_extendModes = [ExtendMode.PAD, ExtendMode.REPEAT, ExtendMode.REFLECT]


@pytest.mark.parametrize("stopOffsets", test_colorStops)
@pytest.mark.parametrize("extend", test_extendModes)
@pytest.mark.parametrize("backendName, surfaceFactory", backends)
def test_colorStops(backendName, surfaceFactory, stopOffsets, extend):
    surface = surfaceFactory(0, 0, 600, 100)
    canvas = surface.canvas
    rectPath = canvas.newPath()
    drawRect(rectPath, 0, 0, 600, 100)
    point1 = (200, 0)
    point2 = (400, 0)
    color1 = (1, 0, 0, 1)
    color2 = (0, 0, 1, 1)
    stop1, stop2 = stopOffsets
    colorLine = [(stop1, color1), (stop2, color2)]
    with canvas.savedState():
        canvas.clipPath(rectPath)
        canvas.fillLinearGradient(colorLine, point1, point2, extend)

    for pos in [200, 400]:
        rectPath = canvas.newPath()
        drawRect(rectPath, pos, 0, 1, 100)
        with canvas.savedState():
            canvas.clipPath(rectPath)
            canvas.fillSolid((0, 0, 0, 1))

    ext = surface.fileExtension
    stopsString = "_".join(str(s) for s in stopOffsets)
    surface.saveImage(
        tmpOutputDir / f"colorStops_{extend.name}_{stopsString}_{backendName}{ext}"
    )


def drawRect(path, x, y, w, h):
    path.moveTo((x, y))
    path.lineTo((x, y + h))
    path.lineTo((x + w, y + h))
    path.lineTo((x + w, y))
    path.closePath()
