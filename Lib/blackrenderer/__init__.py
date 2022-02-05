try:
    from ._version import version as __version__
except ImportError:
    __version__ = "<unknown>"

from .backends import Backend, RequestedFileType
import argparse
import os


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
