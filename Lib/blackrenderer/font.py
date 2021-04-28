from contextlib import contextmanager
from io import BytesIO
import math
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.otTables import PaintFormat
import uharfbuzz as hb


PAINT_NAMES = {v.value: k for k, v in PaintFormat.__members__.items()}


class BlackRendererFont:
    def __init__(self, path):
        with open(path, "rb") as f:
            fontData = f.read()
        file = BytesIO(fontData)
        self.ttFont = TTFont(file, lazy=True)
        # TODO: also handle COLRv0, also handle non-color
        colrTable = self.ttFont["COLR"].table
        self.colrGlyphs = {
            glyph.BaseGlyph: glyph
            for glyph in colrTable.BaseGlyphV1List.BaseGlyphV1Record
        }
        self.layers = colrTable.LayerV1List
        self.palettes = _unpackPalettes(self.ttFont["CPAL"].palettes)
        self.paletteIndex = 0

        self.hbFont = hb.Font(hb.Face(fontData))
        self.location = {}

    def setLocation(self, location):
        self.location = location
        self.hbFont.set_variations(location)

    @contextmanager
    def tmpLocation(self, location):
        # XXX normalized vs user space
        # TODO: wrap these in uharfbuzz:
        # - hb_font_get_var_coords_normalized
        # - hb_font_set_var_coords_normalized
        originalLocation = self.location
        combined = dict(originalLocation)
        combined.update(location)
        self.setLocation(combined)
        yield
        self.setLocation(originalLocation)

    def keys(self):
        return self.colrGlyphs.keys()

    def getGlyphBounds(self, glyphName):
        # TODO: hb must have have an efficient API for this --
        # let's find it and add it to uharfbuzz
        pen = BoundsPen(None)
        self._drawGlyphOutline(glyphName, pen)
        return pen.bounds

    def drawGlyph(self, glyphName, backend):
        glyph = self.colrGlyphs[glyphName]
        self._drawPaint(glyph.Paint, backend)

    # Paint dispatch

    def _drawPaint(self, paint, backend):
        paintName = PAINT_NAMES[paint.Format]
        drawHandler = getattr(self, "_draw" + paintName)
        drawHandler(paint, backend)

    def _drawPaintColrLayers(self, paint, backend):
        n = paint.NumLayers
        s = paint.FirstLayerIndex
        for i in range(s, s + n):
            self._drawPaint(self.layers.Paint[i], backend)

    def _drawPaintSolid(self, paint, backend):
        r, g, b, a = self._getColor(paint.Color.PaletteIndex, paint.Color.Alpha)
        backend.fillSolid((r, g, b, a))

    def _drawPaintLinearGradient(self, paint, backend):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        pt1, pt2 = _reduceThreeAnchorsToTwo(paint)
        pt1, pt2 = (
            _interpolatePoints(pt1, pt2, minStop),
            _interpolatePoints(pt1, pt2, maxStop),
        )
        backend.fillLinearGradient(colorLine, pt1, pt2, paint.ColorLine.Extend)

    def _drawPaintRadialGradient(self, paint, backend):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        startCenter = (paint.x0, paint.y0)
        endCenter = (paint.x1, paint.y1)
        startCenter, endCenter = (
            _interpolatePoints(startCenter, endCenter, minStop),
            _interpolatePoints(startCenter, endCenter, maxStop),
        )
        startRadius = _interpolate(paint.r0, paint.r1, minStop)
        endRadius = _interpolate(paint.r0, paint.r1, maxStop)
        backend.fillRadialGradient(
            colorLine,
            startCenter,
            startRadius,
            endCenter,
            endRadius,
            paint.ColorLine.Extend,
        )

    def _drawPaintSweepGradient(self, paint, backend):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        center = paint.centerX, paint.centerY
        startAngle = _interpolate(paint.startAngle, paint.endAngle, minStop)
        endAngle = _interpolate(paint.startAngle, paint.endAngle, maxStop)
        backend.fillSweepGradient(
            colorLine, center, startAngle, endAngle, paint.ColorLine.Extend
        )

    def _drawPaintGlyph(self, paint, backend):
        path = backend.newPath()
        # paint.Glyph must not be a COLR glyph
        self._drawGlyphOutline(paint.Glyph, path)
        with backend.savedState():
            backend.clipPath(path)
            self._drawPaint(paint.Paint, backend)

    def _drawPaintColrGlyph(self, paint, backend):
        # paint.Glyph must be a COLR glyph (?)
        self.drawGlyph(paint.Glyph, backend)

    def _drawPaintTransform(self, paint, backend):
        t = paint.Transform
        transform = (t.xx, t.yx, t.xy, t.yy, t.dx, t.dy)
        self._applyTransform(transform, paint.Paint, backend)

    def _drawPaintTranslate(self, paint, backend):
        transform = (1, 0, 0, 1, paint.dx, paint.dy)
        self._applyTransform(transform, paint.Paint, backend)

    def _drawPaintRotate(self, paint, backend):
        transform = Transform()
        transform = transform.translate(paint.centerX, paint.centerY)
        transform = transform.rotate(math.radians(paint.angle))
        transform = transform.translate(-paint.centerX, -paint.centerY)
        self._applyTransform(transform, paint.Paint, backend)

    def _drawPaintSkew(self, paint, backend):
        transform = Transform()
        transform = transform.translate(paint.centerX, paint.centerY)
        transform = transform.skew(
            math.radians(paint.xSkewAngle), math.radians(paint.ySkewAngle)
        )
        transform = transform.translate(-paint.centerX, -paint.centerY)
        self._applyTransform(transform, paint.Paint, backend)

    def _drawPaintComposite(self, paint, backend):
        print("_drawPaintComposite")
        # print("Composite with CompositeMode=", paint.CompositeMode)
        # print("Composite source:")
        # ppPaint(paint.SourcePaint, tab+1)
        # print("Composite backdrop:")
        # ppPaint(paint.BackdropPaint, tab+1)

    # Utils

    def _applyTransform(self, transform, paint, backend):
        with backend.savedState():
            backend.transform(transform)
            self._drawPaint(paint, backend)

    def _drawGlyphOutline(self, glyphName, path):
        gid = self.ttFont.getGlyphID(glyphName)
        self.hbFont.draw_glyph_with_pen(gid, path)

    def _getColor(self, colorIndex, alpha):
        if colorIndex == 0xFFFF:
            # TODO: find text foreground color
            r, g, b, a = 0, 0, 0, 1
        else:
            r, g, b, a = self.palettes[self.paletteIndex][colorIndex]
        a *= alpha
        return r, g, b, a

    def _readColorLine(self, colorLineTable):
        return _normalizeColorLine(
            [
                (cs.StopOffset, self._getColor(cs.Color.PaletteIndex, cs.Color.Alpha))
                for cs in colorLineTable.ColorStop
            ]
        )


def _reduceThreeAnchorsToTwo(p):
    # FIXME: make sure the 3 points are not in degenerate position [see COLRv1 spec].
    x02 = p.x2 - p.x0
    y02 = p.y2 - p.y0
    x01 = p.x1 - p.x0
    y01 = p.y1 - p.y0
    squaredNorm02 = x02 * x02 + y02 * y02
    k = (x01 * x02 + y01 * y02) / squaredNorm02
    x = p.x1 - k * x02
    y = p.y1 - k * y02
    return ((p.x0, p.y0), (x, y))


def _normalizeColorLine(colorLine):
    stops = [stopOffset for stopOffset, color in colorLine]
    minStop = min(stops)
    maxStop = max(stops)
    if minStop != maxStop:
        stopExtent = maxStop - minStop
        colorLine = [
            ((stopOffset - minStop) / stopExtent, color)
            for stopOffset, color in colorLine
        ]
    else:
        # Degenerate case. minStop and maxStop are used to reposition
        # the gradients parameters (points, radii, angles), through
        # interpolation. By setting minStop and maxStop to 0 and 1,
        # we at least won't mess up the parameters.
        # FIXME: should the gradient simply not be drawn in this case?
        minStop, maxStop = 0, 1
    return minStop, maxStop, colorLine


def _interpolate(v1, v2, f):
    return v1 + f * (v2 - v1)


def _interpolatePoints(pt1, pt2, f):
    x1, y1 = pt1
    x2, y2 = pt2
    return (x1 + f * (x2 - x1), y1 + f * (y2 - y1))


def _unpackPalettes(palettes):
    return [
        [(c.red / 255, c.green / 255, c.blue / 255, c.alpha / 255) for c in p]
        for p in palettes
    ]
