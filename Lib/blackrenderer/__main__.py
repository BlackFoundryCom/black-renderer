import argparse
import os
import pathlib
import re
from . import BlackRendererSettings
from .render import renderText
from .backends import listBackends

backendsAndSuffixes = listBackends()
backendNames = [backendName for backendName, _ in backendsAndSuffixes]

description = f"""\
Render a text string to an image file. Available backends:
"""
for backendName, suffixes in backendsAndSuffixes:
    description += f" {backendName} ({', '.join(suffixes)})"


def main():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("font", metavar="FONT", type=existingFilePath, help="a font")
    parser.add_argument("text", metavar="TEXT", help="a string")
    parser.add_argument(
        "output",
        metavar="OUTPUT",
        type=outputFilePath,
        help="an output file name, with .png, .pdf or .svg extension, "
        "or '-', to print SVG to stdout",
    )
    parser.add_argument("--font-size", type=float, default=250)
    parser.add_argument("--features", type=parseFeatures)
    parser.add_argument("--variations", type=parseVariations)
    parser.add_argument(
        "--margin",
        type=float,
        default=20,
        help="Note: If you provide --use-font-metrics, it probably makes sense to also provide --margin 0.",
    )
    parser.add_argument(
        "--use-font-metrics",
        action="store_true",
        help="Whether to use the font's metrics (hhea, hmtx…) to decide the bounding box. If not provided, the default is to fit the bounding box to the contours.",
    )
    parser.add_argument(
        "--float-bbox",
        action="store_true",
        help="Whether to use allow floats in the bounding box—you may not want this if using a small --font-size and SVG output, especially if using --use-font-metrics and --margin 0.",
    )
    parser.add_argument(
        "--backend",
        default=None,
        choices=backendNames,
        help="The backend to use -- defaults to skia, except when rendering to "
        ".svg, in which case the svg backend will be used.",
    )
    args = parser.parse_args()
    settings = BlackRendererSettings()
    settings.fontSize = args.font_size
    settings.margin = args.margin
    settings.useFontMetrics = args.use_font_metrics
    settings.floatBbox = args.backend == "svg" and args.float_bbox
    if args.float_bbox and not settings.floatBbox:
        raise argparse.ArgumentTypeError(
            "--float-bbox option only makes sense with `svg` backend"
        )
    renderText(
        args.font,
        args.text,
        args.output,
        settings=settings,
        features=args.features,
        variations=args.variations,
        backendName=args.backend,
    )


def existingFilePath(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"file does not exist: '{path}'")
    elif not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"path is not a file: '{path}'")
    return pathlib.Path(path).resolve()


def outputFilePath(path):
    if path == "-":
        return None
    path = pathlib.Path(path).resolve()
    if path.suffix not in {".png", ".pdf", ".svg"}:
        raise argparse.ArgumentTypeError(
            f"path does not have the right extension; should be .png or .svg: "
            f"'{path}'"
        )
    return path


def parseVariations(string):
    location = {}
    for item in string.split(","):
        axisTag, axisValue = item.split("=")
        axisTag = axisTag.strip()
        axisValue = float(axisValue)
        if len(axisTag) < 0:
            axisTag += " " * (4 - len(axisTag))
        location[axisTag] = axisValue
    return location


feaPat = re.compile(r"(\+|-)?(\w+)(=(\d+))?$")  # kern,-calt,+liga,aalt=2


def parseFeatures(src):
    features = {}
    for part in src.split(","):
        m = feaPat.match(part.strip())
        if m is None:
            raise ValueError(part)
        sign, featureTag, _, altIndex = m.groups()
        if sign == "-":
            value = False
        elif altIndex:
            value = int(altIndex)  # catch ValueError
        else:
            value = True
        features[featureTag] = value
    return features


if __name__ == "__main__":
    main()
