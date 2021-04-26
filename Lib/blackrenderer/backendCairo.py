from contextlib import contextmanager
import os
from fontTools.misc.arrayTools import calcBounds, sectRect
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib.tables.otTables import ExtendMode
import cairo

_extendMap = {
        ExtendMode.PAD: cairo.Extend.PAD,
        ExtendMode.REPEAT: cairo.Extend.REPEAT,
        ExtendMode.REFLECT: cairo.Extend.REFLECT,
        }

class CairoPen(BasePen):
    def __init__(self, context):
        super().__init__(None)
        self.context = context

    def _moveTo(self, pt):
        x, y = pt
        self.context.move_to(x, y)

    def _lineTo(self, pt):
        x, y = pt
        self.context.line_to(x, y)

    def _curveToOne(self, pt1, pt2, pt3):
        x1, y1 = pt1
        x2, y2 = pt2
        x3, y3 = pt3
        self.context.curve_to(x1, y1, x2, y2, x3, y3)

    def _closePath(self):
        self.context.close_path()


class CairoBackend:
    def __init__(self, context):
        self.context = context
        self.clipRect = None
        self._pen = CairoPen(context)

    @staticmethod
    def newPath():
        return RecordingPen()

    @contextmanager
    def savedState(self):
        prevClipRect = self.clipRect
        self.context.save()
        yield
        self.context.restore()
        self.clipRect = prevClipRect

    def transform(self, transform):
        m = cairo.Matrix()
        m.xx, m.yx, m.xy, m.yy, m.x0, m.y0 = transform
        self.context.transform(m)

    def clipPath(self, path):
        self.context.new_path()
        path.replay(self._pen)
        # We calculate the bounds of the new clipping path in device
        # coordinates, as at the time of drawing a solid fill we may
        # be in a different coordinate space.
        x1, y1, x2, y2 = self.context.path_extents()
        points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
        points = [self.context.user_to_device(x, y) for x, y in points]
        clipRect = calcBounds(points)
        if self.clipRect is not None:
            # Our clip gets added to an existing clip, so use intersection
            self.clipRect = sectRect(self.clipRect, clipRect)
        else:
            self.clipRect = clipRect
        self.context.clip()

    def fillSolid(self, color):
        self.context.set_source_rgba(*color)
        self._fill()

    def fillLinearGradient(self, colorLine, pt1, pt2, FTExtend):
        gr = cairo.LinearGradient(pt1[0], pt1[1], pt2[0], pt2[1])
        gr.set_extend(_extendMap[FTExtend])
        # FIXME: one should clip offset below 0 or above 1 (and adjusting the
        # stop color) because Cairo does not seem to accept stops outside of
        # the range [0,1].
        for stop, color in colorLine:
            gr.add_color_stop_rgba(stop, *color)
        self.context.set_source(gr)
        self._fill()

    def fillRadialGradient(self, colorLine, startPt, startRadius, endPt, endRadius, FTExtend):
        gr = cairo.RadialGradient(
            startPt[0], startPt[1], startRadius, endPt[0], endPt[1], endRadius
        )
        gr.set_extend(_extendMap[FTExtend])
        for stop, color in colorLine:
            gr.add_color_stop_rgba(stop, *color)
        self.context.set_source(gr)
        self._fill()

    def fillSweepGradient(self, *args):
        print("fillSweepGradient")
        from random import random

        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite

    def _fill(self):
        # This function is reused in fillSolid() and all 3 fill*Gradient()
        # functions.
        self.context.save()
        self.context.identity_matrix()
        x1, y1, x2, y2 = self.clipRect
        self.context.rectangle(x1, y1, x2 - x1, y2 - y1)
        self.context.fill()
        self.context.restore()


class CairoPixelSurface:
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.context = cairo.Context(self.surface)
        self.context.translate(-x, height + y)
        self.context.scale(1, -1)

    @property
    def backend(self):
        return CairoBackend(self.context)

    def saveImage(self, path):
        self.surface.flush()
        self.surface.write_to_png(os.fspath(path))
        self.surface.finish()
