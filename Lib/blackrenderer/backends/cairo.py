from contextlib import contextmanager
import os
from fontTools.misc.arrayTools import calcBounds, sectRect
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib.tables.otTables import ExtendMode
import cairo
from .base import Backend, Surface


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


class CairoBackend(Backend):
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

    def fillSweepGradient(self, *args):
        print("fillSweepGradient")
        from random import random

        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite

    def _fill(self):
        self.context.save()
        self.context.identity_matrix()
        x1, y1, x2, y2 = self.clipRect
        self.context.rectangle(x1, y1, x2 - x1, y2 - y1)
        self.context.fill()
        self.context.restore()


class CairoPixelSurface(Surface):
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
