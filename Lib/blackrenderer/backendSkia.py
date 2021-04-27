from contextlib import contextmanager
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib.tables.otTables import ExtendMode
import skia

_extendMap = {
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
        x1, y1 = pt1
        x2, y2 = pt2
        x3, y3 = pt3
        self.path.cubicTo(x1, y1, x2, y2, x3, y3)

    def _qCurveToOne(self, pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        self.path.quadTo(x1, y1, x2, y2)

    def _closePath(self):
        self.path.close()


class SkiaBackend:
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

    def fillLinearGradient(self, colorLine, pt1, pt2, extend):
        colors, stops = _unpackColorLine(colorLine)
        shader = skia.GradientShader.MakeLinear(
            points=[pt1, pt2],
            colors=colors,
            positions=stops,
            mode=_extendMap[extend],
        )
        self.canvas.drawPaint(skia.Paint(Shader=shader))

    def fillRadialGradient(
        self, colorLine, startPt, startRadius, endPt, endRadius, extend
    ):
        colors, stops = _unpackColorLine(colorLine)
        shader = skia.GradientShader.MakeTwoPointConical(
            start=startPt,
            startRadius=startRadius,
            end=endPt,
            endRadius=endRadius,
            colors=colors,
            positions=stops,
            mode=_extendMap[extend],
        )
        self.canvas.drawPaint(skia.Paint(Shader=shader))

    def fillSweepGradient(self, *args):
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


class SkiaPixelSurface:
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        self.surface = skia.Surface(width, height)
        self.canvas = self.surface.getCanvas()
        self.canvas.translate(-x, height + y)
        self.canvas.scale(1, -1)

    @property
    def backend(self):
        return SkiaBackend(self.canvas)

    def saveImage(self, path, format=skia.kPNG):
        image = self.surface.makeImageSnapshot()
        image.save(os.fspath(path), format)
