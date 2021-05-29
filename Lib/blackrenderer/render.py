import io
from typing import NamedTuple
import os
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


def renderText(
    fontPath,
    textString,
    outputPath,
    *,
    fontSize=250,
    margin=20,
    features=None,
    variations=None,
    pngSurfaceName="skia",
):
    font = BlackRendererFont(fontPath)
    glyphNames = font.glyphNames

    scaleFactor = fontSize / font.unitsPerEm

    buf = hb.Buffer()
    buf.add_str(textString)
    buf.guess_segment_properties()

    if variations:
        font.setLocation(variations)

    hb.shape(font.hbFont, buf, features)

    infos = buf.glyph_infos
    positions = buf.glyph_positions
    glyphLine = buildGlyphLine(infos, positions, glyphNames)
    bounds = calcGlyphLineBounds(glyphLine, font)
    bounds = scaleRect(bounds, scaleFactor, scaleFactor)
    bounds = insetRect(bounds, -margin, -margin)
    bounds = intRect(bounds)
    if outputPath is None or os.path.splitext(outputPath)[1] == ".svg":
        surfaceClass = getSurfaceClass("svg")
    else:
        surfaceClass = getSurfaceClass(pngSurfaceName)
    surface = surfaceClass(bounds)
    canvas = surface.canvas
    canvas.scale(scaleFactor)
    for glyph in glyphLine:
        with canvas.savedState():
            canvas.translate(glyph.xOffset, glyph.yOffset)
            font.drawGlyph(glyph.name, canvas)
        canvas.translate(glyph.xAdvance, glyph.yAdvance)
    if outputPath is not None:
        surface.saveImage(outputPath)
    else:
        stream = io.BytesIO()
        surface.saveImage(stream)
        print(stream.getvalue().decode("utf-8").rstrip())


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


def calcGlyphLineBounds(glyphLine, font):
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
    return bounds


class GlyphInfo(NamedTuple):
    name: str
    gid: int
    xAdvance: float
    yAdvance: float
    xOffset: float
    yOffset: float
