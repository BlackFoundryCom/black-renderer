from contextlib import contextmanager
import os
from fontTools.misc.arrayTools import calcBounds, sectRect
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib.tables.otTables import ExtendMode
import cairo
from .base import Canvas, Surface


_extendModeMap = {
    ExtendMode.PAD: cairo.Extend.PAD,
    ExtendMode.REPEAT: cairo.Extend.REPEAT,
    ExtendMode.REFLECT: cairo.Extend.REFLECT,
}


class CairoPen(BasePen):
    def __init__(self, context):
        super().__init__(None)
        self.context = context

    def _moveTo(self, pt):
        self.context.move_to(*pt)

    def _lineTo(self, pt):
        self.context.line_to(*pt)

    def _curveToOne(self, pt1, pt2, pt3):
        self.context.curve_to(*pt1, *pt2, *pt3)

    def _closePath(self):
        self.context.close_path()


class CairoCanvas(Canvas):
    def __init__(self, context):
        self.context = context
        self._pen = CairoPen(context)

    @staticmethod
    def newPath():
        return RecordingPen()

    @contextmanager
    def savedState(self):
        self.context.save()
        yield
        self.context.restore()

    def transform(self, transform):
        m = cairo.Matrix()
        m.xx, m.yx, m.xy, m.yy, m.x0, m.y0 = transform
        self.context.transform(m)

    def clipPath(self, path):
        self.context.new_path()
        path.replay(self._pen)
        self.context.clip()

    def fillSolid(self, color):
        self.context.set_source_rgba(*color)
        self._fill()

    def fillLinearGradient(self, colorLine, pt1, pt2, extendMode):
        gr = cairo.LinearGradient(pt1[0], pt1[1], pt2[0], pt2[1])
        gr.set_extend(_extendModeMap[extendMode])
        # FIXME: one should clip offset below 0 or above 1 (and adjusting the
        # stop color) because Cairo does not seem to accept stops outside of
        # the range [0,1].
        for stop, color in colorLine:
            gr.add_color_stop_rgba(stop, *color)
        self.context.set_source(gr)
        self._fill()

    def fillRadialGradient(
        self, colorLine, startCenter, startRadius, endCenter, endRadius, extendMode
    ):
        gr = cairo.RadialGradient(
            startCenter[0],
            startCenter[1],
            startRadius,
            endCenter[0],
            endCenter[1],
            endRadius,
        )
        gr.set_extend(_extendModeMap[extendMode])
        for stop, color in colorLine:
            gr.add_color_stop_rgba(stop, *color)
        self.context.set_source(gr)
        self._fill()

    def fillSweepGradient(self, colorLine, center, startAngle, endAngle, extendMode):
        print("fillSweepGradient")
        from random import random

        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite

    def _fill(self):
        x1, y1, x2, y2 = self.context.clip_extents()
        self.context.rectangle(x1, y1, x2 - x1, y2 - y1)
        self.context.fill()


class CairoPixelSurface(Surface):
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.context = cairo.Context(self.surface)
        self.context.translate(-x, height + y)
        self.context.scale(1, -1)
        self._canvas = CairoCanvas(self.context)

    @property
    def canvas(self):
        return self._canvas

    def saveImage(self, path):
        self.surface.flush()
        self.surface.write_to_png(os.fspath(path))
        self.surface.finish()
