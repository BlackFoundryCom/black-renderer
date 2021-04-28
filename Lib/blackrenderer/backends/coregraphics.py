from contextlib import contextmanager
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib.tables.otTables import ExtendMode
import Quartz as CG
from .base import Backend, Surface


class CGPathPen(BasePen):
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


class CGBackend(Backend):
    def __init__(self, context):
        self.context = context
        self.clipIsEmpty = None

    @staticmethod
    def newPath():
        return CGPathPen()

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
        (x, y), (w, h) = CG.CGPathGetBoundingBox(path.path)
        if w == 0 and h == 0:
            # The path is empty, which causes *no* clip path to be set,
            # which in turn would cause the entire canvas to be filled,
            # so let's prevent that with a flag.
            self.clipIsEmpty = True
        else:
            self.clipIsEmpty = False
            CG.CGContextAddPath(self.context, path.path)
            CG.CGContextClip(self.context)

    def fillSolid(self, color):
        if self.clipIsEmpty:
            return
        # I can't find a way to fill the entire clipping area without specifying
        # a rect. Finding a good rect takes work because of transformations (see
        # backendsCairo), so for now let's abuse CGContextDrawLinearGradient
        # (which doesn't require a rect) and use a gradient with two identical
        # colors.
        colorLine = [(0, color), (1, color)]
        self.fillLinearGradient(colorLine, (0, 0), (1000, 0), ExtendMode.PAD)

    def fillLinearGradient(self, colorLine, pt1, pt2, extendMode):
        if self.clipIsEmpty:
            return
        colors, stops = _unpackColorLine(colorLine)
        gradient = CG.CGGradientCreateWithColors(None, colors, stops)
        CG.CGContextDrawLinearGradient(
            self.context,
            gradient,
            pt1,
            pt2,
            CG.kCGGradientDrawsBeforeStartLocation
            | CG.kCGGradientDrawsAfterEndLocation,
        )

    def fillRadialGradient(
        self, colorLine, startCenter, startRadius, endCenter, endRadius, extendMode
    ):
        if self.clipIsEmpty:
            return
        colors, stops = _unpackColorLine(colorLine)
        gradient = CG.CGGradientCreateWithColors(None, colors, stops)
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

    def fillSweepGradient(self, *args):
        if self.clipIsEmpty:
            return
        print("fillSweepGradient")
        from random import random

        self.fillSolid((1, random(), random(), 1))

    # TODO: blendMode for PaintComposite


def _unpackColorLine(colorLine):
    colors = []
    stops = []
    for stop, color in colorLine:
        colors.append(CG.CGColorCreateGenericRGB(*color))
        stops.append(stop)
    return colors, stops


class CGPixelSurface(Surface):
    fileExtension = ".png"

    def __init__(self, x, y, width, height):
        rgbColorSpace = CG.CGColorSpaceCreateDeviceRGB()
        # rgbColorSpace = CG.CGColorSpaceCreateWithName(CG.kCGColorSpaceSRGB)
        self.context = CG.CGBitmapContextCreate(
            None, width, height, 8, 0, rgbColorSpace, CG.kCGImageAlphaPremultipliedFirst
        )
        CG.CGContextTranslateCTM(self.context, -x, -y)

    @property
    def backend(self):
        return CGBackend(self.context)

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
