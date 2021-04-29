from abc import ABC, abstractmethod
from contextlib import contextmanager


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

    def translate(self, x, y):
        self.transform((1, 0, 0, 1, x, y))

    def scale(self, sx, sy=None):
        if sy is None:
            sy = sx
        self.transform((sx, 0, 0, sy, 0, 0))


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
