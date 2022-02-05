from enum import Enum, auto, unique
from collections import defaultdict
import argparse
import importlib
import os


_surfaces = {
    None: {
        "cairo": "blackrenderer.backends.cairo.CairoPixelSurface",
        "coregraphics": "blackrenderer.backends.coregraphics.CoreGraphicsPixelSurface",
        "skia": "blackrenderer.backends.skia.SkiaPixelSurface",
        "svg": "blackrenderer.backends.svg.SVGSurface",
    },
    ".png": {
        "cairo": "blackrenderer.backends.cairo.CairoPixelSurface",
        "coregraphics": "blackrenderer.backends.coregraphics.CoreGraphicsPixelSurface",
        "skia": "blackrenderer.backends.skia.SkiaPixelSurface",
    },
    ".pdf": {
        "cairo": "blackrenderer.backends.cairo.CairoPDFSurface",
        "coregraphics": "blackrenderer.backends.coregraphics.CoreGraphicsPDFSurface",
        "skia": "blackrenderer.backends.skia.SkiaPDFSurface",
    },
    ".svg": {
        "cairo": "blackrenderer.backends.cairo.CairoSVGSurface",
        "skia": "blackrenderer.backends.skia.SkiaSVGSurface",
        "svg": "blackrenderer.backends.svg.SVGSurface",
    },
}


@unique
class Backend(Enum):
    CAIRO = "cairo"
    COREGRAPHICS = "coregraphics"
    SKIA = "skia"
    PUREPYTHON_SVG = "svg"

    @staticmethod
    def from_filetype_and_backend_name(fileType, backendName):
        if fileType.value != ".svg":
            return Backend.SKIA
        else:
            return Backend.PUREPYTHON_SVG

    @classmethod
    def _missing_(cls, backendName):
        if backendName is None or backendName == "":
            return Backend.PUREPYTHON_SVG
        raise argparse.ArgumentTypeError(f"Non-existent backend: {backendName}")


@unique
class RequestedFileType(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return "." + name.lower()

    PNG = auto()
    PDF = auto()
    SVG = auto()

    @staticmethod
    def from_filename(outputPath):
        if outputPath is None:
            suffix = ".svg"
        else:
            suffix = os.path.splitext(outputPath)[1].lower()
        if suffix != "":
            return RequestedFileType(suffix)
        else:
            return RequestedFileType.SVG

    @classmethod
    def _missing_(cls, value):
        if value == "":
            return RequestedFileType.SVG
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        raise argparse.ArgumentTypeError(f"Unsupported file extension — {value}")


def getSurfaceClass(backend, imageExtension=None):
    if imageExtension is not None and isinstance(imageExtension, RequestedFileType):
        imageExtension = imageExtension.value
    if isinstance(backend, Backend):
        backend = backend.value
    fqName = _surfaces[imageExtension][backend]
    moduleName, className = fqName.rsplit(".", 1)
    try:
        module = importlib.import_module(moduleName)
    except ModuleNotFoundError:
        return None
    return getattr(module, className)


def listBackends():
    backends = defaultdict(list)
    for suffix in _surfaces:
        if suffix is None:
            continue
        for backendName in _surfaces[suffix]:
            backends[backendName].append(suffix)
    return [
        (backendName, sorted(suffixes)) for backendName, suffixes in backends.items()
    ]
