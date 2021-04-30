import pathlib
import pytest
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
    "twemoji": dataDir / "TwemojiMozilla.subset.default.3299.ttf",
}


test_glyphs = [
    ("noto", "uni2693"),
    ("noto", "uni2694"),
    ("noto", "u1F30A"),
    ("noto", "u1F943"),
    ("mutator", "B"),
    ("twemoji", "uni3299"),
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
