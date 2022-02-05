from typing import NamedTuple
from fontTools.misc.arrayTools import (
    scaleRect,
    offsetRect,
    intRect,
    unionRect,
    insetRect,
)
import uharfbuzz as hb
from .font import BlackRendererFont
from .backends import getSurfaceClass
from .backends import Backend, RequestedFileType
import argparse


# Optional command line arguments.
class BlackRendererSettings:
    fontSize = 250.0
    margin = 20.0
    useFontMetrics = False
    floatBbox = False
    backend = Backend.PUREPYTHON_SVG
    fileType = None

    def __init__(self, args):
        self.fontSize = args.font_size
        self.margin = args.margin
        self.useFontMetrics = args.use_font_metrics
        self.fileType = RequestedFileType.from_filename(args.output)
        self.backend = Backend.from_filetype_and_backend_name(
            self.fileType, self.backend
        )
        self.floatBbox = self.backend == Backend.PUREPYTHON_SVG and args.float_bbox

        if args.float_bbox and not self.floatBbox:
            raise argparse.ArgumentTypeError(
                "--float-bbox option only makes sense with `svg` backend"
            )


class BackendUnavailableError(Exception):
    pass


def renderText(
    fontPath,
    textString,
    outputPath,
    settings=None,
    features=None,
    variations=None,
    backendName=None,
):
    if settings is None:
        settings = BlackRendererSettings()
    font = BlackRendererFont(fontPath)
    glyphNames = font.glyphNames

    scaleFactor = settings.fontSize / font.unitsPerEm

    buf = hb.Buffer()
    buf.add_str(textString)
    buf.guess_segment_properties()

    if variations:
        font.setLocation(variations)

    hb.shape(font.hbFont, buf, features)

    infos = buf.glyph_infos
    positions = buf.glyph_positions
    glyphLine = buildGlyphLine(infos, positions, glyphNames)
    bounds = calcGlyphLineBounds(glyphLine, font, settings.useFontMetrics)
    bounds = scaleRect(bounds, scaleFactor, scaleFactor)
    bounds = insetRect(bounds, -settings.margin, -settings.margin)
    if not settings.floatBbox:
        bounds = intRect(bounds)

    surfaceClass = getSurfaceClass(settings.backend, settings.fileType)
    if surfaceClass is None:
        raise BackendUnavailableError(settings.backend.value)

    surface = surfaceClass()
    with surface.canvas(bounds) as canvas:
        canvas.scale(scaleFactor)
        for glyph in glyphLine:
            with canvas.savedState():
                canvas.translate(glyph.xOffset, glyph.yOffset)
                font.drawGlyph(glyph.name, canvas)
            canvas.translate(glyph.xAdvance, glyph.yAdvance)

    if outputPath is not None:
        surface.saveImage(outputPath)
    else:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".svg") as tmp:
            surface.saveImage(tmp.name)
            with open(tmp.name, "rb") as f:
                svgData = f.read().decode("utf-8").rstrip()
        print(svgData)


def buildGlyphLine(infos, positions, glyphNames):
    glyphLine = []
    for info, pos in zip(infos, positions):
        g = GlyphInfo(
            name=glyphNames[info.codepoint],
            gid=info.codepoint,
            xAdvance=pos.x_advance,
            yAdvance=pos.y_advance,
            xOffset=pos.x_offset,
            yOffset=pos.y_offset,
        )
        glyphLine.append(g)
    return glyphLine


def calcGlyphLineBounds(glyphLine, font, useFontMetrics):
    bounds = None
    x, y = 0, 0
    for glyph in glyphLine:
        glyphBounds = font.getGlyphBounds(glyph.name)
        if glyphBounds is None:
            continue
        glyphBounds = offsetRect(glyphBounds, x + glyph.xOffset, y + glyph.yOffset)
        x += glyph.xAdvance
        y += glyph.yAdvance
        if bounds is None:
            bounds = glyphBounds
        else:
            bounds = unionRect(bounds, glyphBounds)
    if useFontMetrics:
        ttf = font.ttFont
        x = 0
        for glyph in glyphLine:
            x += glyph.xAdvance
        bounds = (0, ttf["hhea"].descender, x, ttf["hhea"].ascender)
    return bounds


class GlyphInfo(NamedTuple):
    name: str
    gid: int
    xAdvance: float
    yAdvance: float
    xOffset: float
    yOffset: float
