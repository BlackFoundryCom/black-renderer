from abc import ABC, abstractmethod
from contextlib import contextmanager


class Backend(ABC):
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
    def fillSolid(self, color):
        ...

    @abstractmethod
    def fillLinearGradient(self, colorLine, pt1, pt2, extendMode):
        ...

    @abstractmethod
    def fillRadialGradient(
        self, colorLine, startCenter, startRadius, endCenter, endRadius, extendMode
    ):
        ...

    @abstractmethod
    def fillSweepGradient(self, *args):
        ...


class Surface(ABC):
    fileExtension = ".png"

    @abstractmethod
    def __init__(self, x, y, width, height):
        ...

    @property
    @abstractmethod
    def backend(self):
        ...

    @abstractmethod
    def saveImage(self, path):
        ...
