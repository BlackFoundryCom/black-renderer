from abc import ABC, abstractmethod
from contextlib import contextmanager

from math import pi, ceil, sin, cos
from fontTools.misc.vector import Vector

class Canvas(ABC):
    @abstractmethod
    def __init__(self, context):
        ...

    @staticmethod
    @abstractmethod
    def newPath():
        ...

    @abstractmethod
    @contextmanager
    def savedState(self):
        ...

    @abstractmethod
    def transform(self, transform):
        ...

    @abstractmethod
    def clipPath(self, path):
        ...

    @abstractmethod
    def drawPathSolid(self, path, color):
        ...

    @abstractmethod
    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    # Generic convenience methods

    def translate(self, x, y):
        self.transform((1, 0, 0, 1, x, y))

    def scale(self, sx, sy=None):
        if sy is None:
            sy = sx
        self.transform((sx, 0, 0, sy, 0, 0))

    def drawRectSolid(self, rect, color):
        self.drawPathSolid(self._rectPath(rect), color)

    def drawRectLinearGradient(self, rect, *args, **kwargs):
        self.drawPathLinearGradient(self._rectPath(rect), *args, **kwargs)

    def drawRectRadialGradient(self, rect, *args, **kwargs):
        self.drawPathRadialGradient(self._rectPath(rect), *args, **kwargs)

    def drawRectSweepGradient(self, rect, *args, **kwargs):
        self.drawPathSweepGradient(self._rectPath(rect), *args, **kwargs)

    def _rectPath(self, rect):
        x, y, w, h = rect
        path = self.newPath()
        path.moveTo((x, y))
        path.lineTo((x, y + h))
        path.lineTo((x + w, y + h))
        path.lineTo((x + w, y))
        path.closePath()
        return path

    def _buildSweepGradientPatches(
        self,
        colorLine,
        center,
        radius,
        startAngle,
        endAngle,
        useGouraudShading,
    ):
        patches = []
        # generate a fan of 'triangular' bezier patches, with center 'center' and radius 'radius'
        degToRad = pi/180.0
        if useGouraudShading:
            maxAngle = pi/360.0
            radius = 1.05 * radius # we will use straight-edged triangles
        else:
            maxAngle = pi/10.0
        n = len(colorLine)
        center = Vector(center)
        for i in range(n-1):
            a0, col0 = colorLine[i+0]
            a1, col1 = colorLine[i+1]
            col0 = Vector(col0)
            col1 = Vector(col1)
            a0 = degToRad * (startAngle + a0 * (endAngle - startAngle))
            a1 = degToRad * (startAngle + a1 * (endAngle - startAngle))
            numSplits = int(ceil((a1 - a0) / maxAngle))
            p0 = Vector((cos(a0), sin(a0)))
            color0 = col0
            for a in range(numSplits):
                k = ((a + 1.0) / numSplits)
                angle1 = a0 + k * (a1 - a0)
                color1 = col0 + k * (col1 - col0)
                p1 = Vector((cos(angle1), sin(angle1)))
                P0 = center[0] + radius * p0[0], center[1] + radius * p0[1]
                P1 = center[0] + radius * p1[0], center[1] + radius * p1[1]
                # draw patch
                if useGouraudShading:
                    patches.append(((P0, color0), (P1, color1)))
                else:
                    # compute cubic Bezier antennas (control points) so as to approximate the circular arc p0-p1
                    A = (p0 + p1).normalized()
                    U = Vector((-A[1], A[0])) # tangent to circle at A
                    C0 = A + ((p0 - A).dot(p0) / U.dot(p0)) * U
                    C1 = A + ((p1 - A).dot(p1) / U.dot(p1)) * U
                    C0 = center + radius * (C0 + 0.33333 * (C0 - p0))
                    C1 = center + radius * (C1 + 0.33333 * (C1 - p1))
                    patches.append(((P0, color0), C0, C1, (P1, color1)))
                # move to next patch
                p0 = p1
                color0 = color1
        return patches

class Surface(ABC):
    fileExtension = ".png"

    @abstractmethod
    def __init__(self, x, y, width, height):
        ...

    @property
    @abstractmethod
    def canvas(self):
        ...

    @abstractmethod
    def saveImage(self, path):
        ...
