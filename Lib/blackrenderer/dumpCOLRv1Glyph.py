from functools import singledispatch
from fontTools.ttLib.tables.otTables import ColorLine, Paint
from .font import PAINT_NAMES


def dumpCOLRv1Glyph(font, glyphName):
    print(glyphName)
    glyph = font.colrV1Glyphs[glyphName]
    d = unpackObject(glyph.Paint, font)
    printObject(d, 0)


simpleTypes = (int, float, str, tuple)


@singledispatch
def unpackObject(obj, font):
    d = {}
    for n, v in obj.__dict__.items():
        if hasattr(v, "__dict__"):
            v = unpackObject(v, font)
        d[n] = v
    return d


@unpackObject.register
def unpackPaint(paint: Paint, font):
    paintName = PAINT_NAMES[paint.Format]
    d = {"#": paintName}
    if paintName == "PaintColrLayers":
        n = paint.NumLayers
        s = paint.FirstLayerIndex
        layers = [
            unpackObject(font.colrLayersV1.Paint[i], font) for i in range(s, s + n)
        ]
        d["Layers"] = layers
    else:
        for n, v in paint.__dict__.items():
            if not isinstance(v, simpleTypes):
                v = unpackObject(v, font)
            d[n] = v
    return d


@unpackObject.register
def unpackColorLine(colorLine: ColorLine, font):
    return [
        (
            round(cs.StopOffset, 3),
            color255(font._getColor(cs.Color.PaletteIndex, cs.Color.Alpha)),
        )
        for cs in colorLine.ColorStop
    ]


def color255(color):
    return tuple(round(ch * 255) for ch in color)


@singledispatch
def printObject(obj, level, prefix="  "):
    print("    " * level + prefix + reprItem(obj))


@printObject.register
def printDict(dct: dict, level, prefix="  "):
    for k, v in dct.items():
        if isinstance(v, simpleTypes):
            print("    " * level + prefix + str(k), reprItem(v))
        else:
            print("    " * level + prefix + str(k))
            printObject(v, level + 1)
        prefix = "  "


@printObject.register
def printList(lst: list, level):
    for item in lst:
        printObject(item, level, "- ")


def reprItem(item):
    if isinstance(item, float):
        return str(round(item, 3))
    else:
        return str(item)
