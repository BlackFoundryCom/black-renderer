from contextlib import contextmanager
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib.tables.otTables import ExtendMode
import Quartz as CG
from .base import Canvas, Surface
from .sweepGradient import buildSweepGradientPatches


class CoreGraphicsPathPen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.path = CG.CGPathCreateMutable()

    def _moveTo(self, pt):
        CG.CGPathMoveToPoint(self.path, None, *pt)

    def _lineTo(self, pt):
        CG.CGPathAddLineToPoint(self.path, None, *pt)

    def _curveToOne(self, pt1, pt2, pt3):
        CG.CGPathAddCurveToPoint(self.path, None, *pt1, *pt2, *pt3)

    def _qCurveToOne(self, pt1, pt2):
        CG.CGPathAddQuadCurveToPoint(self.path, None, *pt1, *pt2)

    def _closePath(self):
        CG.CGPathCloseSubpath(self.path)


class CoreGraphicsCanvas(Canvas):
    def __init__(self, context):
        self.context = context
        self.clipIsEmpty = None

    @staticmethod
    def newPath():
        return CoreGraphicsPathPen()

    @contextmanager
    def savedState(self):
        clipIsEmpty = self.clipIsEmpty
        CG.CGContextSaveGState(self.context)
        yield
        CG.CGContextRestoreGState(self.context)
        self.clipIsEmpty = clipIsEmpty

    def transform(self, transform):
        CG.CGContextConcatCTM(self.context, transform)

    def clipPath(self, path):
        if CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            # The path is empty, which causes *no* clip path to be set,
            # which in turn would cause the entire canvas to be filled,
            # so let's prevent that with a flag.
            self.clipIsEmpty = True
        else:
            self.clipIsEmpty = False
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)

    def drawPathSolid(self, path, color):
        if self.clipIsEmpty:
            return
        CG.CGContextAddPath(self.context, path.path)
        CG.CGContextSetRGBFillColor(self.context, *color)
        CG.CGContextFillPath(self.context)

    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        if self.clipIsEmpty or CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            return
        colors, stops = _unpackColorLine(colorLine)
        gradient = CG.CGGradientCreateWithColors(None, colors, stops)
        with self.savedState():
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)
            self.transform(gradientTransform)
            CG.CGContextDrawLinearGradient(
                self.context,
                gradient,
                pt1,
                pt2,
                CG.kCGGradientDrawsBeforeStartLocation
                | CG.kCGGradientDrawsAfterEndLocation,
            )

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
        if self.clipIsEmpty or CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            return
        colors, stops = _unpackColorLine(colorLine)
        gradient = CG.CGGradientCreateWithColors(None, colors, stops)
        with self.savedState():
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)
            self.transform(gradientTransform)
            CG.CGContextDrawRadialGradient(
                self.context,
                gradient,
                startCenter,
                startRadius,
                endCenter,
                endRadius,
                CG.kCGGradientDrawsBeforeStartLocation
                | CG.kCGGradientDrawsAfterEndLocation,
            )

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
        from math import sqrt

        if self.clipIsEmpty or CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            return
        with self.savedState():
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)
            self.transform(gradientTransform)
            # find current path' extent
            bb = CG.CGContextGetClipBoundingBox(self.context)
            x1, y1 = bb.origin.x, bb.origin.y
            x2 = x1 + bb.size.width
            y2 = y1 + bb.size.height
            maxX = max(d * d for d in (x1 - center[0], x2 - center[0]))
            maxY = max(d * d for d in (y1 - center[1], y2 - center[1]))
            R = sqrt(maxX + maxY)
            # compute the triangle fan approximating the sweep gradient
            patches = buildSweepGradientPatches(
                colorLine, center, R, startAngle, endAngle, useGouraudShading=True
            )
            CG.CGContextSetAllowsAntialiasing(self.context, False)
            for (P0, color0), (P1, color1) in patches:
                color = 0.5 * (color0 + color1)
                CG.CGContextMoveToPoint(self.context, center[0], center[1])
                CG.CGContextAddLineToPoint(self.context, P0[0], P0[1])
                CG.CGContextAddLineToPoint(self.context, P1[0], P1[1])
                CG.CGContextSetRGBFillColor(self.context, *color)
                CG.CGContextFillPath(self.context)
            CG.CGContextSetAllowsAntialiasing(self.context, True)

    # TODO: blendMode for PaintComposite


def _unpackColorLine(colorLine):
    colors = []
    stops = []
    for stop, color in colorLine:
        colors.append(CG.CGColorCreateGenericRGB(*color))
        stops.append(stop)
    return colors, stops


class CoreGraphicsPixelSurface(Surface):
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        rgbColorSpace = CG.CGColorSpaceCreateDeviceRGB()
        # rgbColorSpace = CG.CGColorSpaceCreateWithName(CG.kCGColorSpaceSRGB)
        self.context = CG.CGBitmapContextCreate(
            None, width, height, 8, 0, rgbColorSpace, CG.kCGImageAlphaPremultipliedFirst
        )
        CG.CGContextTranslateCTM(self.context, -x, -y)
        self._canvas = CoreGraphicsCanvas(self.context)

    @property
    def canvas(self):
        return self._canvas

    def saveImage(self, path):
        image = CG.CGBitmapContextCreateImage(self.context)
        saveImageAsPNG(image, path)


def saveImageAsPNG(image, path):
    path = os.path.abspath(path).encode("utf-8")
    url = CG.CFURLCreateFromFileSystemRepresentation(None, path, len(path), False)
    assert url is not None
    dest = CG.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    assert dest is not None
    CG.CGImageDestinationAddImage(dest, image, None)
    CG.CGImageDestinationFinalize(dest)
