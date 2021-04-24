from contextlib import contextmanager
import os
from fontTools.pens.basePen import BasePen
import skia


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
    def transform(self, transform):
        matrix = skia.Matrix()
        matrix.setAffine(transform)
        self.canvas.save()
        self.canvas.concat(matrix)
        yield
        self.canvas.restore()

    @contextmanager
    def clip(self, path):
        self.canvas.save()
        self.canvas.clipPath(path.path)
        yield
        self.canvas.restore()

    def fillSolid(self, color):
        self.canvas.drawColor(skia.Color4f(tuple(color)))

    def fillLinearGradient(self, *args):
        print("fillLinearGradient")
        from random import random
        self.fillSolid((1, random(), random(), 1))

    def fillRadialGradient(self, *args):
        print("fillRadialGradient")
        from random import random
        self.fillSolid((1, random(), random(), 1))

    def fillSweepGradient(self, *args):
        print("fillSweepGradient")
        from random import random
        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite


class PixelSurface:
    def __init__(self, x, y, width, height):
        self.surface = skia.Surface(width, height)
        canvas = self.canvas
        canvas.translate(0, height)
        canvas.scale(1, -1)
        canvas.translate(-x, -y)

    @property
    def canvas(self):
        return self.surface.getCanvas()

    def saveImage(self, path, format=skia.kPNG):
        image = self.surface.makeImageSnapshot()
        image.save(os.fspath(path), format)
