from functools import reduce
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
from . import BlackRendererSettings
from .font import BlackRendererFont
from .backends import getSurfaceClass


class BackendUnavailableError(Exception):
    pass


def renderText(
    fontPath,
    textString,
    outputPath,
    *,
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
    if outputPath is None:
        suffix = ".svg"
    else:
        suffix = os.path.splitext(outputPath)[1].lower()
    if backendName is None:
        if suffix == ".svg":
            backendName = "svg"
        else:
            backendName = "skia"
    surfaceClass = getSurfaceClass(backendName, suffix)
    if surfaceClass is None:
        raise BackendUnavailableError(backendName)

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
    glyphLineBounds = [font.getGlyphBounds(glyph.name) for glyph in glyphLine]
    x, y = 0, 0
    for (glyphBounds, glyph) in zip(glyphLineBounds, glyphLine):
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
