import pathlib
import pytest
from fontTools.misc.arrayTools import scaleRect, intRect
from blackrenderer.font import BlackRendererFont
from blackrenderer.backends import getSurfaceClass
from blackrenderer.backends.pathCollector import BoundsCanvas, PathCollectorCanvas
from compareImages import compareImages


testDir = pathlib.Path(__file__).resolve().parent
dataDir = testDir / "data"
expectedOutputDir = testDir / "expectedOutput"
tmpOutputDir = testDir / "tmpOutput"
if not tmpOutputDir.exists():
    tmpOutputDir.mkdir()


backends = [
    (name, getSurfaceClass(name)) for name in ["cairo", "coregraphics", "skia", "svg"]
]
backends = [(name, surface) for name, surface in backends if surface is not None]


testFonts = {
    "noto": dataDir / "noto-glyf_colr_1.ttf",
    "mutator": dataDir / "MutatorSans.ttf",
    "twemoji": dataDir / "TwemojiMozilla.subset.default.3299.ttf",
    "more_samples": dataDir / "more_samples-glyf_colr_1.ttf",
    "crash": dataDir / "crash.subset.otf",
}


test_glyphs = [
    ("noto", "uni2693", None),
    ("noto", "uni2694", None),
    ("noto", "u1F30A", None),
    ("noto", "u1F943", None),
    ("mutator", "B", None),
    ("mutator", "D", {"wdth": 1000}),
    ("twemoji", "uni3299", None),
    ("more_samples", "cross_glyph", None),
    ("more_samples", "skew_0_15_center_500.0_500.0", None),
    ("more_samples", "skew_-10_20_center_500.0_500.0", None),
    ("more_samples", "skew_-10_20_center_1000_1000", None),
    ("more_samples", "transform_matrix_1_0_0_1_125_125", None),
    ("more_samples", "transform_matrix_1.5_0_0_1.5_0_0", None),
    ("more_samples", "transform_matrix_0.9659_0.2588_-0.2588_0.9659_0_0", None),
    ("more_samples", "transform_matrix_1.0_0.0_0.6_1.0_-300.0_0.0", None),
    ("more_samples", "clip_box_top_left", None),
    ("more_samples", "clip_box_bottom_left", None),
    ("more_samples", "clip_box_bottom_right", None),
    ("more_samples", "clip_box_top_right", None),
    ("more_samples", "clip_box_center", None),
    ("more_samples", "composite_DEST_OVER", None),
    ("more_samples", "composite_XOR", None),
    ("more_samples", "composite_OVERLAY", None),
    ("more_samples", "composite_SRC_IN", None),
    ("more_samples", "composite_PLUS", None),
    ("more_samples", "composite_LIGHTEN", None),
    ("more_samples", "composite_MULTIPLY", None),
    ("more_samples", "clip_shade_center", None),
    ("more_samples", "clip_shade_top_left", None),
    ("more_samples", "clip_shade_bottom_left", None),
    ("more_samples", "clip_shade_bottom_right", None),
    ("more_samples", "clip_shade_top_right", None),
    ("more_samples", "inset_clipped_radial_reflect", None),
    ("more_samples", "sweep", None),
    ("more_samples", "transformed_sweep", None),
    ("more_samples", "composite_colr_glyph", None),
    ("more_samples", "linear_repeat_0_1", None),
    ("more_samples", "linear_repeat_0.2_0.8", None),
    ("more_samples", "linear_repeat_0_1.5", None),
    ("more_samples", "linear_repeat_0.5_1.5", None),
    ("more_samples", "scale_0.5_1.5_center_500.0_500.0", None),
    ("more_samples", "scale_1.5_1.5_center_500.0_500.0", None),
    ("more_samples", "scale_0.5_1.5_center_0_0", None),
    ("more_samples", "scale_1.5_1.5_center_0_0", None),
    ("more_samples", "scale_0.5_1.5_center_1000_1000", None),
    ("more_samples", "scale_1.5_1.5_center_1000_1000", None),
    ("more_samples", "linear_gradient_extend_mode_pad", None),
    ("more_samples", "linear_gradient_extend_mode_repeat", None),
    ("more_samples", "linear_gradient_extend_mode_reflect", None),
    ("more_samples", "radial_gradient_extend_mode_pad", None),
    ("more_samples", "radial_gradient_extend_mode_repeat", None),
    ("more_samples", "radial_gradient_extend_mode_reflect", None),
    ("more_samples", "rotate_10_center_0_0", None),
    ("more_samples", "rotate_-10_center_1000_1000", None),
    ("more_samples", "rotate_25_center_500.0_500.0", None),
    ("more_samples", "rotate_-15_center_500.0_500.0", None),
    ("more_samples", "skew_25_0_center_0_0", None),
    ("more_samples", "skew_25_0_center_500.0_500.0", None),
    ("more_samples", "skew_0_15_center_0_0", None),
    ("more_samples", "upem_box_glyph", None),
]


@pytest.mark.parametrize("fontName, glyphName, location", test_glyphs)
@pytest.mark.parametrize("backendName, surfaceClass", backends)
def test_renderGlyph(backendName, surfaceClass, fontName, glyphName, location):
    font = BlackRendererFont(testFonts[fontName])
    font.setLocation(location)

    scaleFactor = 1 / 4
    boundingBox = font.getGlyphBounds(glyphName)
    boundingBox = scaleRect(boundingBox, scaleFactor, scaleFactor)
    boundingBox = intRect(boundingBox)

    surface = surfaceClass()
    ext = surface.fileExtension
    with surface.canvas(boundingBox) as canvas:
        canvas.scale(scaleFactor)
        font.drawGlyph(glyphName, canvas)

    fileName = f"glyph_{fontName}_{glyphName}_{backendName}{ext}"
    expectedPath = expectedOutputDir / fileName
    outputPath = tmpOutputDir / fileName
    surface.saveImage(outputPath)
    diff = compareImages(expectedPath, outputPath)
    assert diff < 0.00012, diff


def test_pathCollector():
    font = BlackRendererFont(testFonts["noto"])
    canvas = PathCollectorCanvas()
    font.drawGlyph("uni2693", canvas)
    assert len(canvas.paths) == 6


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


vectorBackends = [
    ("cairo", ".pdf"),
    ("cairo", ".svg"),
    ("skia", ".pdf"),
    ("skia", ".svg"),
    ("coregraphics", ".pdf"),
]


@pytest.mark.parametrize("backendName, imageSuffix", vectorBackends)
def test_vectorBackends(backendName, imageSuffix):
    fontName = "noto"
    glyphName = "u1F943"
    surfaceClass = getSurfaceClass(backendName, imageSuffix)
    if surfaceClass is None:
        pytest.skip(f"{backendName} not available")
    assert surfaceClass.fileExtension == imageSuffix

    font = BlackRendererFont(testFonts[fontName])
    boundingBox = font.getGlyphBounds(glyphName)

    surface = surfaceClass()
    with surface.canvas(boundingBox) as canvas:
        font.drawGlyph(glyphName, canvas)
    fileName = f"vector_{fontName}_{glyphName}_{backendName}{imageSuffix}"
    expectedPath = expectedOutputDir / fileName
    outputPath = tmpOutputDir / fileName
    surface.saveImage(outputPath)
    # For now, just be happy the code works.
    # - Cairo PDFs contain the creation date
    # - CoreGraphics PDFs are weirdly different while looking the same
    # assert expectedPath.read_bytes() == outputPath.read_bytes()
    diff = compareImages(expectedPath, outputPath)
    assert diff < 0.00012, diff


def test_recursive():
    # https://github.com/BlackFoundryCom/black-renderer/issues/56
    # https://github.com/justvanrossum/fontgoggles/issues/213
    glyphName = "hah-ar"
    font = BlackRendererFont(testFonts["crash"])
    boundingBox = font.getGlyphBounds(glyphName)
    surfaceClass = getSurfaceClass("svg", ".svg")
    surface = surfaceClass()
    with surface.canvas(boundingBox) as canvas:
        with pytest.raises(RecursionError):
            font.drawGlyph(glyphName, canvas)
