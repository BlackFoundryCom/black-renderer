from contextlib import contextmanager
import logging
from fontTools.misc.transform import Transform
from fontTools.pens.basePen import BasePen
from fontTools.misc.xmlWriter import XMLWriter
from io import StringIO


logger = logging.getLogger(__name__)


class SVGPath(BasePen):
    def __init__(self, glyphSet=None):
        super().__init__(glyphSet)
        self.segments = []

    def _moveTo(self, pt):
        self.segments.append("M" + formatCoord(pt))

    def _lineTo(self, pt):
        cx, cy = self._getCurrentPoint()
        dx = pt[0] - cx
        dy = pt[1] - cy
        if dx and dy:
            self.segments.append("l" + formatCoord((dx, dy)))
        elif dx:
            self.segments.append("h" + formatNumber(dx))
        else:
            self.segments.append("v" + formatNumber(dy))

    def _curveToOne(self, pt1, pt2, pt3):
        cx, cy = self._getCurrentPoint()
        points = [formatCoord((x - cx, y - cy)) for x, y in [pt1, pt2, pt3]]
        self.segments.append("c" + " ".join(points))

    def _qCurveToOne(self, pt1, pt2):
        cx, cy = self._getCurrentPoint()
        points = [formatCoord((x - cx, y - cy)) for x, y in [pt1, pt2]]
        self.segments.append("q" + " ".join(points))

    def _closePath(self):
        self.segments.append("Z")

    def svgPath(self):
        return " ".join(self.segments)


class SVGBackend:
    def __init__(self, transform):
        self.clipStack = ()
        self.currentTransform = transform
        self.elements = []

    @staticmethod
    def newPath():
        return SVGPath()

    @contextmanager
    def savedState(self):
        prevTransform = self.currentTransform
        prevClipStack = self.clipStack
        yield
        self.currentTransform = prevTransform
        self.clipStack = prevClipStack

    def transform(self, transform):
        self.currentTransform = self.currentTransform.transform(transform)

    def clipPath(self, path):
        self.clipStack = self.clipStack + ((path.svgPath(), self.currentTransform),)

    def fillSolid(self, color):
        assert len(self.clipStack) > 0
        fillPath, fillTransform = self.clipStack[-1]
        clipPath, clipTransform = None, None
        if len(self.clipStack) >= 2:
            clipPath, clipTransform = self.clipStack[-2]
            if len(self.clipStack) > 2:
                logger.warning(
                    "SVG backend does not support more than two nested clip paths"
                )
        paint = RGBAPaint(color)
        self.elements.append((fillPath, fillTransform, clipPath, clipTransform, paint))

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


class RGBAPaint(tuple):
    pass


class SVGSurface:
    fileExtension = ".svg"

    def __init__(self, x, y, width, height):
        self.viewBox = x, y, width, height
        transform = Transform(1, 0, 0, -1, x, height + y)
        transform = transform.translate(-x, -y)
        self.backend = SVGBackend(transform)

    def saveImage(self, path):
        with open(path, "w") as f:
            f.write(self.toSVG())

    def toSVG(self):
        elements = self.backend.elements
        clipPaths = {}
        for fillPath, fillTransform, clipPath, clipTransform, paint in elements:
            clipKey = clipPath, clipTransform
            if clipPath is not None and clipKey not in clipPaths:
                clipPaths[clipKey] = f"clip_{len(clipPaths)}"

        f = StringIO()
        w = XMLWriter(f)
        docAttrs = [
            ("width", formatNumber(self.viewBox[2])),
            ("height", formatNumber(self.viewBox[3])),
            ("preserveAspectRatio", "xMinYMin slice"),
            ("viewBox", " ".join(formatNumber(n) for n in self.viewBox)),
            ("version", "1.1"),
            ("xmlns", "http://www.w3.org/2000/svg"),
            ("xmlns:xlink", "http://www.w3.org/1999/xlink"),
        ]
        w.begintag("svg", docAttrs)
        w.newline()
        for (clipPath, clipTransform), clipID in clipPaths.items():
            w.begintag("clipPath", id=clipID)
            w.newline()
            w.simpletag(
                "path", [("d", clipPath), ("transform", formatMatrix(clipTransform))]
            )
            w.newline()
            w.endtag("clipPath")
            w.newline()

        for fillPath, fillTransform, clipPath, clipTransform, paint in elements:
            attrs = [("d", fillPath)]
            attrs += colorToSVGAttrs(paint)  # XXX needs work for gradients
            attrs.append(("transform", formatMatrix(fillTransform)))
            if clipPath is not None:
                clipKey = clipPath, clipTransform
                attrs.append(("clip-path", f"url({clipPaths[clipKey]})"))
            w.simpletag("path", attrs)
            w.newline()

        w.endtag("svg")
        w.newline()
        return f.getvalue()


def formatCoord(pt):
    x, y = pt
    return "%s,%s" % (formatNumber(x), formatNumber(y))


def formatNumber(n):
    i = int(n)
    if i == n:
        return str(i)
    else:
        return str(round(n, 4))  # 4 decimals enough?


def colorToSVGAttrs(color):
    attrs = []
    opacity = 1
    if len(color) == 4:
        opacity = color[3]
        color = color[:3]
    attrs.append(("fill", formatColor(color)))
    if opacity != 1:
        attrs.append(("fill-opacity", opacity))
    return attrs


def formatColor(color):
    if not color:
        return "none"
    assert len(color) == 3
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in color)


def formatMatrix(t):
    assert len(t) == 6
    return "matrix(%s,%s,%s,%s,%s,%s)" % tuple(formatNumber(v) for v in t)
