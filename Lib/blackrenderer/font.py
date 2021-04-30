from contextlib import contextmanager
from io import BytesIO
import math
from fontTools.misc.transform import Transform, Identity
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

        self.textColor = (0, 0, 0, 1)
        self.colrV0Glyphs = {}
        self.colrV1Glyphs = {}

        if "COLR" in self.ttFont:
            colrTable = self.ttFont["COLR"]
            if colrTable.version == 0:
                self.colrV0Glyphs = colrTable.ColorLayers
            else:  # >= 1
                # Hm, a little sad we need to use an internal static method
                self.colrV0Glyphs = colrTable._decompileColorLayersV0(colrTable.table)
                colrTable = colrTable.table
                self.colrV1Glyphs = {
                    glyph.BaseGlyph: glyph
                    for glyph in colrTable.BaseGlyphV1List.BaseGlyphV1Record
                }
                self.colrLayersV1 = colrTable.LayerV1List

        if "CPAL" in self.ttFont:
            self.palettes = _unpackPalettes(self.ttFont["CPAL"].palettes)
        self.paletteIndex = 0

        self.hbFont = hb.Font(hb.Face(fontData))
        self.location = {}

    @property
    def unitsPerEm(self):
        return self.hbFont.face.upem

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

    @property
    def glyphNames(self):
        return self.ttFont.getGlyphOrder()

    @property
    def colrV0GlyphNames(self):
        return self.colrV0Glyphs.keys()

    @property
    def colrV1GlyphNames(self):
        return self.colrV1Glyphs.keys()

    def getGlyphBounds(self, glyphName):
        # TODO: hb must have have an efficient API for this --
        # let's find it and add it to uharfbuzz
        pen = BoundsPen(None)
        if glyphName in self.colrV1Glyphs or glyphName not in self.colrV0Glyphs:
            self._drawGlyphOutline(glyphName, pen)
        else:
            # For COLRv0, we take the union of all layer bounds
            pen = BoundsPen(None)
            for layer in self.colrV0Glyphs[glyphName]:
                self._drawGlyphOutline(layer.name, pen)
        return pen.bounds

    def drawGlyph(self, glyphName, canvas):
        glyph = self.colrV1Glyphs.get(glyphName)
        if glyph is not None:
            self.currentTransform = Identity
            self.currentPath = None
            self._drawGlyphCOLRv1(glyph, canvas)
            return
        glyph = self.colrV0Glyphs.get(glyphName)
        if glyph is not None:
            self._drawGlyphCOLRv0(glyph, canvas)
            return
        else:
            self._drawGlyphNoColor(glyphName, canvas)

    def _drawGlyphNoColor(self, glyphName, canvas):
        path = canvas.newPath()
        self._drawGlyphOutline(glyphName, path)
        canvas.drawPathSolid(path, self.textColor)

    def _drawGlyphCOLRv0(self, layers, canvas):
        for layer in layers:
            path = canvas.newPath()
            self._drawGlyphOutline(layer.name, path)
            canvas.drawPathSolid(path, self._getColor(layer.colorID, 1))

    def _drawGlyphCOLRv1(self, glyph, canvas):
        self._drawPaint(glyph.Paint, canvas)

    # COLRv1 Paint dispatch

    def _drawPaint(self, paint, canvas):
        paintName = PAINT_NAMES[paint.Format]
        drawHandler = getattr(self, "_draw" + paintName)
        drawHandler(paint, canvas)

    def _drawPaintColrLayers(self, paint, canvas):
        n = paint.NumLayers
        s = paint.FirstLayerIndex
        with self._ensureClipAndSetPath(canvas, None):
            for i in range(s, s + n):
                self._drawPaint(self.colrLayersV1.Paint[i], canvas)

    def _drawPaintSolid(self, paint, canvas):
        color = self._getColor(paint.Color.PaletteIndex, paint.Color.Alpha)
        canvas.drawPathSolid(self.currentPath, color)

    def _drawPaintLinearGradient(self, paint, canvas):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        pt1, pt2 = _reduceThreeAnchorsToTwo(paint)
        pt1, pt2 = (
            _interpolatePoints(pt1, pt2, minStop),
            _interpolatePoints(pt1, pt2, maxStop),
        )
        canvas.drawPathLinearGradient(
            self.currentPath,
            colorLine,
            pt1,
            pt2,
            paint.ColorLine.Extend,
            self.currentTransform,
        )

    def _drawPaintRadialGradient(self, paint, canvas):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        startCenter = (paint.x0, paint.y0)
        endCenter = (paint.x1, paint.y1)
        startCenter, endCenter = (
            _interpolatePoints(startCenter, endCenter, minStop),
            _interpolatePoints(startCenter, endCenter, maxStop),
        )
        startRadius = _interpolate(paint.r0, paint.r1, minStop)
        endRadius = _interpolate(paint.r0, paint.r1, maxStop)
        canvas.drawPathRadialGradient(
            self.currentPath,
            colorLine,
            startCenter,
            startRadius,
            endCenter,
            endRadius,
            paint.ColorLine.Extend,
            self.currentTransform,
        )

    def _drawPaintSweepGradient(self, paint, canvas):
        minStop, maxStop, colorLine = self._readColorLine(paint.ColorLine)
        center = paint.centerX, paint.centerY
        startAngle = _interpolate(paint.startAngle, paint.endAngle, minStop)
        endAngle = _interpolate(paint.startAngle, paint.endAngle, maxStop)
        canvas.drawPathSweepGradient(
            self.currentPath,
            colorLine,
            center,
            startAngle,
            endAngle,
            paint.ColorLine.Extend,
            self.currentTransform,
        )

    def _drawPaintGlyph(self, paint, canvas):
        path = canvas.newPath()
        # paint.Glyph must not be a COLR glyph
        self._drawGlyphOutline(paint.Glyph, path)
        with self._ensureClipAndSetPath(canvas, path):
            self._drawPaint(paint.Paint, canvas)

    def _drawPaintColrGlyph(self, paint, canvas):
        with self._ensureClipAndSetPath(canvas, None):
            self._drawGlyphCOLRv1(paint.Glyph, canvas)

    def _drawPaintTransform(self, paint, canvas):
        t = paint.Transform
        transform = (t.xx, t.yx, t.xy, t.yy, t.dx, t.dy)
        self._applyTransform(transform, paint.Paint, canvas)

    def _drawPaintTranslate(self, paint, canvas):
        transform = (1, 0, 0, 1, paint.dx, paint.dy)
        self._applyTransform(transform, paint.Paint, canvas)

    def _drawPaintRotate(self, paint, canvas):
        transform = Transform()
        transform = transform.translate(paint.centerX, paint.centerY)
        transform = transform.rotate(math.radians(paint.angle))
        transform = transform.translate(-paint.centerX, -paint.centerY)
        self._applyTransform(transform, paint.Paint, canvas)

    def _drawPaintSkew(self, paint, canvas):
        transform = Transform()
        transform = transform.translate(paint.centerX, paint.centerY)
        transform = transform.skew(
            math.radians(paint.xSkewAngle), math.radians(paint.ySkewAngle)
        )
        transform = transform.translate(-paint.centerX, -paint.centerY)
        self._applyTransform(transform, paint.Paint, canvas)

    def _drawPaintComposite(self, paint, canvas):
        with self._ensureClipAndSetPath(canvas, None):
            print("_drawPaintComposite")
        # print("Composite with CompositeMode=", paint.CompositeMode)
        # print("Composite source:")
        # ppPaint(paint.SourcePaint, tab+1)
        # print("Composite backdrop:")
        # ppPaint(paint.BackdropPaint, tab+1)

    # Utils

    @contextmanager
    def _ensureClipAndSetPath(self, canvas, path):
        if self.currentPath is not None:
            clipPath = self.currentPath
            clipTransform = self.currentTransform
            with canvas.savedState(), self._setPath(path), self._setTransform(Identity):
                canvas.transform(clipTransform)
                canvas.clipPath(clipPath)
                yield
        elif path is not None:
            with self._setPath(path), self._setTransform(Identity):
                yield
        else:
            yield

    @contextmanager
    def _setPath(self, path):
        currentPath = self.currentPath
        self.currentPath = path
        yield
        self.currentPath = currentPath

    @contextmanager
    def _setTransform(self, transform):
        currentTransform = self.currentTransform
        self.currentTransform = transform
        yield
        self.currentTransform = currentTransform

    def _applyTransform(self, transform, paint, canvas):
        self.currentTransform = self.currentTransform.transform(transform)
        self._drawPaint(paint, canvas)

    def _drawGlyphOutline(self, glyphName, path):
        gid = self.ttFont.getGlyphID(glyphName)
        self.hbFont.draw_glyph_with_pen(gid, path)

    def _getColor(self, colorIndex, alpha):
        if colorIndex == 0xFFFF:
            # TODO: find text foreground color
            r, g, b, a = self.textColor
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
