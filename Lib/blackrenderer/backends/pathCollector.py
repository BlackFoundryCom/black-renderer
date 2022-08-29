from contextlib import contextmanager
from fontTools.misc.arrayTools import calcBounds
from fontTools.misc.transform import Identity
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from .base import Canvas, Surface

class PathCollectorRecordingPen(RecordingPen):
    def annotate(self, method, data):
        self.method = method
        self.data = data
    
    def __repr__(self):
        return f"PathCollectorRecordingPen({self.method}{list(self.data.keys())})"


class PathCollectorCanvas(Canvas):
    def __init__(self):
        self.init()

    def init(self):
        self.paths = []
        self.currentTransform = Identity

    def _addPath(self, path, method, data):
        if self.currentTransform != Identity:
            path = transformPath(path, self.currentTransform)
        path.annotate(method, data)
        self.paths.append(path)

    def newPath(self):
        return PathCollectorRecordingPen()

    @contextmanager
    def savedState(self):
        savedTransform = self.currentTransform
        yield
        self.currentTransform = savedTransform

    @contextmanager
    def compositeMode(self, compositeMode):
        yield

    def transform(self, transform):
        self.currentTransform = self.currentTransform.transform(transform)

    def clipPath(self, path):
        self._addPath(path, "clipPath", dict())

    def drawPathSolid(self, path, color):
        self._addPath(path, "drawPathSolid", dict(color=color))

    def drawPathLinearGradient(
        self, path, colorLine, pt1, pt2, extendMode, gradientTransform
    ):
        self._addPath(path, "drawPathLinearGradient", dict(
            colorLine=colorLine,
            pt1=pt1,
            pt2=pt2,
            extendMode=extendMode,
            gradientTransform=gradientTransform,
        ))

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
        self._addPath(path, "drawPathRadialGradient", dict(
            colorLine=colorLine,
            startCenter=startCenter,
            startRadius=startRadius,
            endCenter=endCenter,
            endRadius=endRadius,
            extendMode=extendMode,
            gradientTransform=gradientTransform,
        ))

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
        self._addPath(path, "drawPathSweepGradient", dict(
            colorLine=colorLine,
            center=center,
            startAngle=startAngle,
            endAngle=endAngle,
            extendMode=extendMode,
            gradientTransform=gradientTransform,
        ))


class PathCollectorSurface(Surface):
    fileExtension = None

    def __init__(self):
        self.paths = None
        pass

    @contextmanager
    def canvas(self, boundingBox):
        canvas = PathCollectorCanvas()
        yield canvas
        self.paths = canvas.paths

    def saveImage(self, path):
        raise Exception("PathCollectorSurface cannot be saved")


class PointCollector:
    def __init__(self):
        self.points = []

    def moveTo(self, pt):
        self.points.append(pt)

    def lineTo(self, pt):
        self.points.append(pt)

    def curveTo(self, *pts):
        self.points.extend(pts)

    qCurveTo = curveTo

    def closePath(self):
        pass

    def endPath(self):
        pass


class BoundsCanvas(PathCollectorCanvas):
    def init(self):
        self.points = []
        self.currentTransform = Identity

    @property
    def bounds(self):
        return calcBounds(self.points)

    def _addPath(self, path, method, data):
        points = path.points
        if self.currentTransform != Identity:
            points = self.currentTransform.transformPoints(points)
        self.points.extend(points)

    def newPath(self):
        return PointCollector()


def transformPath(path, transform):
    transformedPath = RecordingPen()
    tpen = TransformPen(transformedPath, transform)
    path.replay(tpen)
    # to keep the path ref the same
    path.value = transformedPath.value
    return path
