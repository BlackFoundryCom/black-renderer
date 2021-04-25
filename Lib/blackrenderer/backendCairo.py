from contextlib import contextmanager
import os
from fontTools.misc.arrayTools import calcBounds, sectRect
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
import cairo


class CairoPen(BasePen):

    def __init__(self, context):
        super().__init__(None)
        self._context = context

    def _moveTo(self, pt):
        x, y = pt
        self._context.move_to(x, y)

    def _lineTo(self, pt):
        x, y = pt
        self._context.line_to(x, y)

    def _curveToOne(self, pt1, pt2, pt3):
        x1, y1 = pt1
        x2, y2 = pt2
        x3, y3 = pt3
        self._context.curve_to(x1, y1, x2, y2, x3, y3)

    def _closePath(self):
        self._context.close_path()


class CairoBackend:
    def __init__(self, canvas):
        self.canvas = canvas
        self.clipRect = None
        self._pen = CairoPen(canvas)

    @staticmethod
    def newPath():
        return RecordingPen()

    @contextmanager
    def savedState(self):
        prevClipRect = self.clipRect
        self.canvas.save()
        yield
        self.canvas.restore()
        self.clipRect = prevClipRect

    def transform(self, transform):
        m = cairo.Matrix()
        m.xx, m.xy, m.yx, m.yy, m.x0, m.y0 = transform
        self.canvas.transform(m)

    def clipPath(self, path):
        self.canvas.new_path()
        path.replay(self._pen)
        # We calculate the bounds of the new clipping path in device
        # coordinates, as at the time of drawing a solid fill we may
        # be in a different coordinate space.
        x1, y1, x2, y2 = self.canvas.path_extents()
        points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
        points = [self.canvas.user_to_device(x, y) for x, y in points]
        clipRect = calcBounds(points)
        if self.clipRect is not None:
            # Our clip gets added to an existing clip, so use intersection
            self.clipRect = sectRect(self.clipRect, clipRect)
        else:
            self.clipRect = clipRect
        self.canvas.clip()

    def fillSolid(self, color):
        r, g, b, a = color
        self.canvas.set_source_rgba(r, g, b, a)
        self.canvas.save()
        self.canvas.identity_matrix()
        x1, y1, x2, y2 = self.clipRect
        self.canvas.rectangle(x1, y1, x2 - x1, y2 - y1)
        self.canvas.fill()
        self.canvas.restore()

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


class CairoPixelSurface:
    def __init__(self, x, y, width, height):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.canvas = cairo.Context(self.surface)
        # self.canvas.rectangle(0, 0, width, height)
        # self.canvas.set_source_rgba(1,1,1,1)
        # self.canvas.fill()
        self.canvas.translate(0, height)
        self.canvas.scale(1, -1)
        self.canvas.translate(-x, -y)

    def saveImage(self, path):
        self.surface.flush()
        self.surface.write_to_png(os.fspath(path))
        self.surface.finish()
