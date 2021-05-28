from contextlib import contextmanager
import logging
from typing import NamedTuple
from fontTools.misc.transform import Transform
from fontTools.pens.basePen import BasePen
from fontTools.misc import etree as ET
from fontTools.ttLib.tables.otTables import ExtendMode
from .base import Canvas, Surface


logger = logging.getLogger(__name__)


_extendModeMap = {
    ExtendMode.PAD: "pad",
    ExtendMode.REPEAT: "repeat",
    ExtendMode.REFLECT: "reflect",
}


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


class SVGCanvas(Canvas):
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

    @contextmanager
    def compositeMode(self, compositeMode):
        yield

    def transform(self, transform):
        self.currentTransform = self.currentTransform.transform(transform)

    def clipPath(self, path):
        self.clipStack = tupleAppend(
            self.clipStack, (path.svgPath(), self.currentTransform)
        )

    def drawPathSolid(self, path, color):
        self._addElement(path.svgPath(), self.currentTransform, RGBAPaint(color), None)

    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        gradient = LinearGradientPaint(tuple(colorLine), pt1, pt2, extendMode)
        self._addElement(
            path.svgPath(), self.currentTransform, gradient, gradientTransform
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
        gradient = RadialGradientPaint(
            tuple(colorLine), startCenter, startRadius, endCenter, endRadius, extendMode
        )
        self._addElement(
            path.svgPath(), self.currentTransform, gradient, gradientTransform
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
        self.drawPathSolid(path, colorLine[0][1])

    # TODO: blendMode for PaintComposite

    def _addElement(self, fillPath, fillTransform, paint, gradientTransform):
        clipPath, clipTransform = None, None
        if self.clipStack:
            clipPath, clipTransform = self.clipStack[-1]
            if len(self.clipStack) > 1:
                # FIXME: intersect clip paths with pathops
                logger.warning(
                    "SVG canvas does not support more than two nested clip paths"
                )
        self.elements.append(
            (fillPath, fillTransform, clipPath, clipTransform, paint, gradientTransform)
        )


class RGBAPaint(tuple):
    pass


class LinearGradientPaint(NamedTuple):
    colorLine: tuple
    pt1: tuple
    pt2: tuple
    extendMode: str

    def toSVG(self, gradientID, transform):
        attrNumbers = [
            ("x1", self.pt1[0]),
            ("y1", self.pt1[1]),
            ("x2", self.pt2[0]),
            ("y2", self.pt2[1]),
        ]
        return _gradientToSVG(
            "linearGradient",
            gradientID,
            self.extendMode,
            self.colorLine,
            transform,
            attrNumbers,
        )


class RadialGradientPaint(NamedTuple):
    colorLine: tuple
    pt1: tuple
    radius1: float
    pt2: tuple
    radius2: float
    extendMode: str

    def toSVG(self, gradientID, transform):
        attrNumbers = [
            ("fx", self.pt1[0]),
            ("fy", self.pt1[1]),
            ("fr", self.radius1),
            ("cx", self.pt2[0]),
            ("cy", self.pt2[1]),
            ("r", self.radius2),
        ]
        return _gradientToSVG(
            "radialGradient",
            gradientID,
            self.extendMode,
            self.colorLine,
            transform,
            attrNumbers,
        )


def _gradientToSVG(
    gradientTag, gradientID, extendMode, colorLine, transform, attrNumbers
):
    element = ET.Element(
        gradientTag,
        id=gradientID,
        spreadMethod=_extendModeMap[extendMode],
        gradientUnits="userSpaceOnUse",
    )
    for attrName, value in attrNumbers:
        element.attrib[attrName] = formatNumber(value)
    if transform != (1, 0, 0, 1, 0, 0):
        element.attrib["gradientTransform"] = formatMatrix(transform)
    for stop, rgba in colorLine:
        stopElement = ET.SubElement(element, "stop")
        stopElement.attrib["offset"] = f"{round(stop * 100)}%"
        for attr, value in colorToSVGAttrs(rgba, "stop-color", "stop-opacity"):
            stopElement.attrib[attr] = value
    return element


class SVGSurface(Surface):
    fileExtension = ".svg"

    def __init__(self, x, y, width, height):
        self.viewBox = x, y, width, height
        transform = Transform(1, 0, 0, -1, 0, height + 2 * y)
        self._canvas = SVGCanvas(transform)

    @property
    def canvas(self):
        return self._canvas

    def saveImage(self, pathOrFile):
        if hasattr(pathOrFile, "write"):
            self.writeSVG(pathOrFile)
        else:
            with open(pathOrFile, "wb") as f:
                self.writeSVG(f)

    def writeSVG(self, stream):
        elements = self.canvas.elements
        clipPaths = {}
        gradients = {}
        for fillPath, fillT, clipPath, clipT, paint, paintT in elements:
            clipKey = clipPath, clipT
            if clipPath is not None and clipKey not in clipPaths:
                clipPaths[clipKey] = f"clip_{len(clipPaths)}"
            gradientKey = paint, paintT
            if not isinstance(paint, RGBAPaint) and gradientKey not in gradients:
                gradients[gradientKey] = f"gradient_{len(gradients)}"

        root = ET.Element(
            "svg",
            width=formatNumber(self.viewBox[2]),
            height=formatNumber(self.viewBox[3]),
            preserveAspectRatio="xMinYMin slice",
            viewBox=" ".join(formatNumber(n) for n in self.viewBox),
            version="1.1",
            xmlns="http://www.w3.org/2000/svg",
        )

        # root.attrib["xmlns:link"] = "http://www.w3.org/1999/xlink"

        if gradients:
            defs = ET.SubElement(root, "defs")
            for (gradient, gradientTransform), gradientID in gradients.items():
                defs.append(gradient.toSVG(gradientID, gradientTransform))

        for (clipPath, clipTransform), clipID in clipPaths.items():
            clipElement = ET.SubElement(root, "clipPath", id=clipID)
            ET.SubElement(
                clipElement, "path", d=clipPath, transform=formatMatrix(clipTransform)
            )

        for fillPath, fillT, clipPath, clipT, paint, paintT in elements:
            attrs = [("d", fillPath)]
            if isinstance(paint, RGBAPaint):
                attrs += colorToSVGAttrs(paint)
            else:
                attrs.append(("fill", f"url(#{gradients[paint, paintT]})"))
            attrs.append(("transform", formatMatrix(fillT)))
            if clipPath is not None:
                clipKey = clipPath, clipTransform
                attrs.append(("clip-path", f"url(#{clipPaths[clipKey]})"))
            ET.SubElement(root, "path", dict(attrs))

        tree = ET.ElementTree(root)
        tree.write(stream, pretty_print=True, xml_declaration=True)


def formatCoord(pt):
    x, y = pt
    return "%s,%s" % (formatNumber(x), formatNumber(y))


def formatNumber(n):
    i = int(n)
    if i == n:
        return str(i)
    else:
        return str(round(n, 4))  # 4 decimals enough?


def colorToSVGAttrs(color, fillAttr="fill", opacityAttr="fill-opacity"):
    attrs = []
    opacity = 1
    if len(color) == 4:
        opacity = color[3]
        color = color[:3]
    attrs.append((fillAttr, formatColor(color)))
    if opacity != 1:
        attrs.append((opacityAttr, formatNumber(opacity)))
    return attrs


def formatColor(color):
    if not color:
        return "none"
    assert len(color) == 3
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in color)


def formatMatrix(t):
    assert len(t) == 6
    return "matrix(%s,%s,%s,%s,%s,%s)" % tuple(formatNumber(v) for v in t)


def tupleAppend(tpl, item):
    return tpl + (item,)
