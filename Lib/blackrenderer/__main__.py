import argparse
import os
import pathlib
import re
from .render import renderText


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("font", metavar="FONT", type=existingFilePath, help="a font")
    parser.add_argument("text", metavar="TEXT", help="a string")
    parser.add_argument(
        "output",
        metavar="OUTPUT",
        type=outputFilePath,
        help="an output file name, with .png or .svg extension, "
        "or '-', to print SVG to stdout",
    )
    parser.add_argument("--font-size", type=float, default=250)
    parser.add_argument("--features", type=parseFeatures)
    parser.add_argument("--variations", type=parseVariations)
    parser.add_argument("--margin", type=float, default=20)
    parser.add_argument(
        "--backend",
        default="skia",
        choices=["skia", "cairo", "coregraphics"],
        help="The backend to use when rendering to .png",
    )
    args = parser.parse_args()
    renderText(
        args.font,
        args.text,
        args.output,
        fontSize=args.font_size,
        margin=args.margin,
        features=args.features,
        variations=args.variations,
        pngSurfaceName=args.backend,
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
    if path.suffix not in {".png", ".svg"}:
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
