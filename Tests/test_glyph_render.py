import pathlib
import pytest
from blackrenderer.font import BlackRendererFont
from blackrenderer.backends import getSurface
from blackrenderer.backends.pathCollector import BoundsCanvas, PathCollectorCanvas
from compareImages import compareImages


testDir = pathlib.Path(__file__).resolve().parent
dataDir = testDir / "data"
expectedOutputDir = testDir / "expectedOutput"
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
    "more_samples": dataDir / "more_samples-glyf_colr_1.ttf",
}


test_glyphs = [
    ("noto", "uni2693", None),
    ("noto", "uni2694", None),
    ("noto", "u1F30A", None),
    ("noto", "u1F943", None),
    ("mutator", "B", None),
    ("mutator", "D", {"wdth": 1000}),
    ("twemoji", "uni3299", None),
    ("more_samples", "sweep", None),
    # ("more_samples", "composite_colr_glyph", None),
    ("more_samples", "linear_repeat_0_1", None),
    ("more_samples", "linear_repeat_0.2_0.8", None),
    ("more_samples", "linear_repeat_0_1.5", None),
    ("more_samples", "linear_repeat_0.5_1.5", None),
    ("more_samples", "transformed_sweep", None),
]


@pytest.mark.parametrize("fontName, glyphName, location", test_glyphs)
@pytest.mark.parametrize("backendName, surfaceFactory", backends)
def test_renderGlyph(backendName, surfaceFactory, fontName, glyphName, location):
    font = BlackRendererFont(testFonts[fontName])
    font.setLocation(location)

    minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

    surface = surfaceFactory(minX, minY, maxX - minX, maxY - minY)
    ext = surface.fileExtension
    font.drawGlyph(glyphName, surface.canvas)

    fileName = f"glyph_{fontName}_{glyphName}_{backendName}{ext}"
    expectedPath = expectedOutputDir / fileName
    outputPath = tmpOutputDir / fileName
    surface.saveImage(outputPath)
    diff = compareImages(expectedPath, outputPath)
    assert diff < 0.0001, diff


def test_pathCollector():
    font = BlackRendererFont(testFonts["noto"])
    canvas = PathCollectorCanvas()
    font.drawGlyph("uni2693", canvas)
    assert len(canvas.paths) == 2


def test_boundsCanvas():
    font = BlackRendererFont(testFonts["mutator"])
    canvas = BoundsCanvas()
    font.drawGlyph("A", canvas)
    assert (20, 0, 376, 700) == canvas.bounds

    font.setLocation({"wdth": 1000})
    canvas = BoundsCanvas()
    font.drawGlyph("A", canvas)
    assert (50, 0, 1140, 700) == canvas.bounds

    font = BlackRendererFont(testFonts["more_samples"])
    canvas = BoundsCanvas()
    font.drawGlyph("transformed_sweep", canvas)
    assert (317, 154, 1183, 846) == tuple(round(v) for v in canvas.bounds)
