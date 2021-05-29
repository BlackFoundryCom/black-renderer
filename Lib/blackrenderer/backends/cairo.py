from contextlib import contextmanager
import os
from math import sqrt
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib.tables.otTables import CompositeMode, ExtendMode
import cairo
from .base import Canvas, Surface
from .sweepGradient import buildSweepGradientPatches


_compositeModeMap = {
    CompositeMode.CLEAR: cairo.OPERATOR_CLEAR,
    CompositeMode.SRC: cairo.OPERATOR_SOURCE,
    CompositeMode.DEST: cairo.OPERATOR_DEST,
    CompositeMode.SRC_OVER: cairo.OPERATOR_OVER,
    CompositeMode.DEST_OVER: cairo.OPERATOR_DEST_OVER,
    CompositeMode.SRC_IN: cairo.OPERATOR_IN,
    CompositeMode.DEST_IN: cairo.OPERATOR_DEST_IN,
    CompositeMode.SRC_OUT: cairo.OPERATOR_OUT,
    CompositeMode.DEST_OUT: cairo.OPERATOR_DEST_OUT,
    CompositeMode.SRC_ATOP: cairo.OPERATOR_ATOP,
    CompositeMode.DEST_ATOP: cairo.OPERATOR_DEST_ATOP,
    CompositeMode.XOR: cairo.OPERATOR_XOR,
    CompositeMode.SCREEN: cairo.OPERATOR_SCREEN,
    CompositeMode.OVERLAY: cairo.OPERATOR_OVERLAY,
    CompositeMode.DARKEN: cairo.OPERATOR_DARKEN,
    CompositeMode.LIGHTEN: cairo.OPERATOR_LIGHTEN,
    CompositeMode.COLOR_DODGE: cairo.OPERATOR_COLOR_DODGE,
    CompositeMode.COLOR_BURN: cairo.OPERATOR_COLOR_BURN,
    CompositeMode.HARD_LIGHT: cairo.OPERATOR_HARD_LIGHT,
    CompositeMode.SOFT_LIGHT: cairo.OPERATOR_SOFT_LIGHT,
    CompositeMode.DIFFERENCE: cairo.OPERATOR_DIFFERENCE,
    CompositeMode.EXCLUSION: cairo.OPERATOR_EXCLUSION,
    CompositeMode.MULTIPLY: cairo.OPERATOR_MULTIPLY,
    CompositeMode.HSL_HUE: cairo.OPERATOR_HSL_HUE,
    CompositeMode.HSL_SATURATION: cairo.OPERATOR_HSL_SATURATION,
    CompositeMode.HSL_COLOR: cairo.OPERATOR_HSL_COLOR,
    CompositeMode.HSL_LUMINOSITY: cairo.OPERATOR_HSL_LUMINOSITY,
}


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

    @contextmanager
    def compositeMode(self, compositeMode):
        self.context.push_group()
        yield
        self.context.pop_group_to_source()
        self.context.set_operator(_compositeModeMap[compositeMode])
        self.context.paint()

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
        self.context.save()
        self.context.new_path()
        path.replay(self._pen)
        self.context.clip()
        self.transform(gradientTransform)
        # alloc the mesh pattern
        pat = cairo.MeshPattern()
        # find current path' extent
        x1, y1, x2, y2 = self.context.clip_extents()
        maxX = max(d * d for d in (x1 - center[0], x2 - center[0]))
        maxY = max(d * d for d in (y1 - center[1], y2 - center[1]))
        R = sqrt(maxX + maxY)
        patches = buildSweepGradientPatches(
            colorLine, center, R, startAngle, endAngle, useGouraudShading=False
        )
        for (P0, color0), C0, C1, (P1, color1) in patches:
            # draw patch
            pat.begin_patch()
            pat.move_to(center[0], center[1])
            pat.line_to(P0[0], P0[1])
            pat.curve_to(C0[0], C0[1], C1[0], C1[1], P1[0], P1[1])
            pat.line_to(center[0], center[1])
            pat.set_corner_color_rgba(0, *color0)
            pat.set_corner_color_rgba(1, *color0)
            pat.set_corner_color_rgba(2, *color1)
            pat.set_corner_color_rgba(3, *color1)
            pat.end_patch()
        self.context.set_source(pat)
        self.context.paint()
        self.context.restore()

    # TODO: blendMode for PaintComposite)

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

    def __init__(self, boundingBox):
        x, y, xMax, yMax = boundingBox
        width = xMax - x
        height = yMax - y
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
