from abc import ABC, abstractmethod
from contextlib import contextmanager


class Canvas(ABC):
    @abstractmethod
    def newPath(self):
        ...

    @abstractmethod
    @contextmanager
    def savedState(self):
        ...

    @abstractmethod
    @contextmanager
    def compositeMode(self, compositeMode):
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
