try:
    from ._version import version as __version__
except ImportError:
    __version__ = "<unknown>"

import argparse
import os
from enum import Enum, auto, unique


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


# Optional command line arguments.
class BlackRendererSettings:
    fontSize = 250.0
    margin = 20.0
    useFontMetrics = False
    floatBbox = False
    backend = Backend.PUREPYTHON_SVG
    fileType = None

    def __init__(self, args):
        self.fontSize = args.font_size
        self.margin = args.margin
        self.useFontMetrics = args.use_font_metrics
        self.fileType = RequestedFileType.from_filename(args.output)
        self.backend = Backend.from_filetype_and_backend_name(
            self.fileType, self.backend
        )
        self.floatBbox = self.backend == Backend.PUREPYTHON_SVG and args.float_bbox

        if args.float_bbox and not self.floatBbox:
            raise argparse.ArgumentTypeError(
                "--float-bbox option only makes sense with `svg` backend"
            )
