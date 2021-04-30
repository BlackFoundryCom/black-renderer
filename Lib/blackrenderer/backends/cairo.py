from contextlib import contextmanager
import os
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

    def drawPathSolid(self, path, color):
        self.context.set_source_rgba(*color)
        self.context.new_path()
        path.replay(self._pen)
        self.context.fill()

    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        gr = cairo.LinearGradient(pt1[0], pt1[1], pt2[0], pt2[1])
        gr.set_extend(_extendModeMap[extendMode])
        for stop, color in colorLine:
            gr.add_color_stop_rgba(stop, *color)
        self._drawGradient(path, gr, gradientTransform)

    def drawPathRadialGradient(
        self,
        path,
        colorLine,
        startCenter,
        startRadius,
        endCenter,
        endRadius,
        extendMode,
        gradientTransform,
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
        self._drawGradient(path, gr, gradientTransform)

    def drawPathSweepGradient(
        self,
        path,
        colorLine,
        center,
        startAngle,
        endAngle,
        extendMode,
        gradientTransform,
    ):
        self.drawPathSolid(path, colorLine[0][1])

    # TODO: blendMode for PaintComposite

    def _drawGradient(self, path, gradient, gradientTransform):
        self.context.new_path()
        path.replay(self._pen)
        self.context.save()
        self.transform(gradientTransform)
        self.context.set_source(gradient)
        self.context.fill()
        self.context.restore()


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
