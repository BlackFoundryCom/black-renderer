from contextlib import contextmanager
from math import sqrt
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib.tables.otTables import CompositeMode, ExtendMode
from CoreFoundation import CFDataCreateMutable
import Quartz as CG
from .base import Canvas, Surface
from .sweepGradient import buildSweepGradientPatches


_compositeModeMap = {
    CompositeMode.CLEAR: CG.kCGBlendModeClear,
    CompositeMode.SRC: CG.kCGBlendModeCopy,
    CompositeMode.DEST: CG.kCGBlendModeNormal,  # This is wrong, but is worked around in canvas.compositeMode()
    CompositeMode.SRC_OVER: CG.kCGBlendModeNormal,
    CompositeMode.DEST_OVER: CG.kCGBlendModeDestinationOver,
    CompositeMode.SRC_IN: CG.kCGBlendModeSourceIn,
    CompositeMode.DEST_IN: CG.kCGBlendModeDestinationIn,
    CompositeMode.SRC_OUT: CG.kCGBlendModeSourceOut,
    CompositeMode.DEST_OUT: CG.kCGBlendModeDestinationOut,
    CompositeMode.SRC_ATOP: CG.kCGBlendModeSourceAtop,
    CompositeMode.DEST_ATOP: CG.kCGBlendModeDestinationAtop,
    CompositeMode.XOR: CG.kCGBlendModeXOR,
    CompositeMode.PLUS: CG.kCGBlendModePlusLighter,
    CompositeMode.SCREEN: CG.kCGBlendModeScreen,
    CompositeMode.OVERLAY: CG.kCGBlendModeOverlay,
    CompositeMode.DARKEN: CG.kCGBlendModeDarken,
    CompositeMode.LIGHTEN: CG.kCGBlendModeLighten,
    CompositeMode.COLOR_DODGE: CG.kCGBlendModeColorDodge,
    CompositeMode.COLOR_BURN: CG.kCGBlendModeColorBurn,
    CompositeMode.HARD_LIGHT: CG.kCGBlendModeHardLight,
    CompositeMode.SOFT_LIGHT: CG.kCGBlendModeSoftLight,
    CompositeMode.DIFFERENCE: CG.kCGBlendModeDifference,
    CompositeMode.EXCLUSION: CG.kCGBlendModeExclusion,
    CompositeMode.MULTIPLY: CG.kCGBlendModeMultiply,
    CompositeMode.HSL_HUE: CG.kCGBlendModeHue,
    CompositeMode.HSL_SATURATION: CG.kCGBlendModeSaturation,
    CompositeMode.HSL_COLOR: CG.kCGBlendModeColor,
    CompositeMode.HSL_LUMINOSITY: CG.kCGBlendModeLuminosity,
}


_sRGBColorSpace = CG.CGColorSpaceCreateWithName(CG.kCGColorSpaceSRGB)


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

    @contextmanager
    def compositeMode(self, compositeMode):
        CG.CGContextSaveGState(self.context)
        if compositeMode == CompositeMode.DEST:
            # Workaround for CG not having a blend mode corresponding
            # with CompositeMode.DEST. Setting alpha to 0 should be
            # equivalent.
            CG.CGContextSetAlpha(self.context, 0.0)
        else:
            CG.CGContextSetBlendMode(self.context, _compositeModeMap[compositeMode])
        CG.CGContextBeginTransparencyLayer(self.context, None)
        yield
        CG.CGContextEndTransparencyLayer(self.context)
        CG.CGContextRestoreGState(self.context)

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
        CG.CGContextSetFillColorWithColor(
            self.context, CG.CGColorCreate(_sRGBColorSpace, color)
        )
        CG.CGContextFillPath(self.context)

    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        if self.clipIsEmpty or CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            return
        colors, stops = _unpackColorLine(colorLine)
        gradient = CG.CGGradientCreateWithColors(_sRGBColorSpace, colors, stops)
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
        gradient = CG.CGGradientCreateWithColors(_sRGBColorSpace, colors, stops)
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
        if self.clipIsEmpty or CG.CGPathGetBoundingBox(path.path) == CG.CGRectNull:
            return
        with self.savedState():
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)
            self.transform(gradientTransform)
            # find current path' extent
            (x1, y1), (w, h) = CG.CGContextGetClipBoundingBox(self.context)
            x2 = x1 + w
            y2 = y1 + h
            maxX = max(d * d for d in (x1 - center[0], x2 - center[0]))
            maxY = max(d * d for d in (y1 - center[1], y2 - center[1]))
            R = sqrt(maxX + maxY)
            # compute the triangle fan approximating the sweep gradient
            patches = buildSweepGradientPatches(
                colorLine, center, R, startAngle, endAngle, useGouraudShading=True
            )
            CG.CGContextBeginTransparencyLayer(self.context, None)
            CG.CGContextSetAllowsAntialiasing(self.context, False)
            for (P0, color0), (P1, color1) in patches:
                color = 0.5 * (color0 + color1)
                CG.CGContextMoveToPoint(self.context, center[0], center[1])
                CG.CGContextAddLineToPoint(self.context, P0[0], P0[1])
                CG.CGContextAddLineToPoint(self.context, P1[0], P1[1])
                CG.CGContextSetFillColorWithColor(
                    self.context, CG.CGColorCreate(_sRGBColorSpace, color)
                )
                CG.CGContextFillPath(self.context)
            CG.CGContextSetAllowsAntialiasing(self.context, True)
            CG.CGContextEndTransparencyLayer(self.context)

    # TODO: blendMode for PaintComposite


def _unpackColorLine(colorLine):
    colors = []
    stops = []
    for stop, color in colorLine:
        colors.append(CG.CGColorCreate(_sRGBColorSpace, color))
        stops.append(stop)
    return colors, stops


class CoreGraphicsPixelSurface(Surface):
    fileExtension = ".png"

    def __init__(self):
        self.context = None

    @contextmanager
    def canvas(self, boundingBox):
        x, y, xMax, yMax = boundingBox
        width = xMax - x
        height = yMax - y
        self._setupCGContext(x, y, width, height)
        yield CoreGraphicsCanvas(self.context)

    def _setupCGContext(self, x, y, width, height):
        self.context = CG.CGBitmapContextCreate(
            None,
            width,
            height,
            8,
            0,
            _sRGBColorSpace,
            CG.kCGImageAlphaPremultipliedFirst,
        )
        CG.CGContextTranslateCTM(self.context, -x, -y)

    def saveImage(self, path):
        image = CG.CGBitmapContextCreateImage(self.context)
        saveImageAsPNG(image, path)


class CoreGraphicsPDFSurface(CoreGraphicsPixelSurface):
    fileExtension = ".pdf"

    @contextmanager
    def canvas(self, boundingBox):
        with super().canvas(boundingBox) as canvas:
            CG.CGContextBeginPage(self.context, self._mediaBox)
            yield canvas
            CG.CGContextEndPage(self.context)

    def _setupCGContext(self, x, y, width, height):
        if self.context is None:
            self._mediaBox = ((x, y), (width, height))
            self._data = CFDataCreateMutable(None, 0)
            consumer = CG.CGDataConsumerCreateWithCFData(self._data)
            self.context = CG.CGPDFContextCreate(consumer, self._mediaBox, None)
        return self.context

    def saveImage(self, path):
        CG.CGPDFContextClose(self.context)
        with open(path, "wb") as f:
            f.write(self._data)


def saveImageAsPNG(image, path):
    path = os.path.abspath(path).encode("utf-8")
    url = CG.CFURLCreateFromFileSystemRepresentation(None, path, len(path), False)
    assert url is not None
    dest = CG.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    assert dest is not None
    CG.CGImageDestinationAddImage(dest, image, None)
    CG.CGImageDestinationFinalize(dest)
