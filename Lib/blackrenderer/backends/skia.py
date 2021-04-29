from contextlib import contextmanager
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib.tables.otTables import ExtendMode
import skia
from .base import Canvas, Surface


_extendModeMap = {
    ExtendMode.PAD: skia.TileMode.kClamp,
    ExtendMode.REPEAT: skia.TileMode.kRepeat,
    ExtendMode.REFLECT: skia.TileMode.kMirror,
}


class SkiaPath(BasePen):
    def __init__(self):
        super().__init__(None)
        self.path = skia.Path()

    def _moveTo(self, pt):
        self.path.moveTo(*pt)

    def _lineTo(self, pt):
        self.path.lineTo(*pt)

    def _curveToOne(self, pt1, pt2, pt3):
        self.path.cubicTo(*pt1, *pt2, *pt3)

    def _qCurveToOne(self, pt1, pt2):
        self.path.quadTo(*pt1, *pt2)

    def _closePath(self):
        self.path.close()


class SkiaCanvas(Canvas):
    def __init__(self, canvas):
        self.canvas = canvas

    @staticmethod
    def newPath():
        return SkiaPath()

    @contextmanager
    def savedState(self):
        self.canvas.save()
        yield
        self.canvas.restore()

    def transform(self, transform):
        matrix = skia.Matrix()
        matrix.setAffine(transform)
        self.canvas.concat(matrix)

    def clipPath(self, path):
        self.canvas.clipPath(path.path, doAntiAlias=True)

    def fillSolid(self, color):
        self.canvas.drawColor(skia.Color4f(tuple(color)))

    def fillLinearGradient(self, colorLine, pt1, pt2, extendMode):
        colors, stops = _unpackColorLine(colorLine)
        shader = skia.GradientShader.MakeLinear(
            points=[pt1, pt2],
            colors=colors,
            positions=stops,
            mode=_extendModeMap[extendMode],
        )
        self.canvas.drawPaint(skia.Paint(Shader=shader))

    def fillRadialGradient(
        self, colorLine, startCenter, startRadius, endCenter, endRadius, extendMode
    ):
        colors, stops = _unpackColorLine(colorLine)
        shader = skia.GradientShader.MakeTwoPointConical(
            start=startCenter,
            startRadius=startRadius,
            end=endCenter,
            endRadius=endRadius,
            colors=colors,
            positions=stops,
            mode=_extendModeMap[extendMode],
        )
        self.canvas.drawPaint(skia.Paint(Shader=shader))

    def fillSweepGradient(self, colorLine, center, startAngle, endAngle, extendMode):
        print("fillSweepGradient")
        from random import random

        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite


def _unpackColorLine(colorLine):
    colors = []
    stops = []
    for stop, color in colorLine:
        colors.append(int(skia.Color4f(tuple(color))))
        stops.append(stop)
    return colors, stops


class SkiaPixelSurface(Surface):
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        self.surface = skia.Surface(width, height)
        self.skCanvas = self.surface.getCanvas()
        self.skCanvas.translate(-x, height + y)
        self.skCanvas.scale(1, -1)
        self._canvas = SkiaCanvas(self.skCanvas)

    @property
    def canvas(self):
        return self._canvas

    def saveImage(self, path, format=skia.kPNG):
        image = self.surface.makeImageSnapshot()
        image.save(os.fspath(path), format)
