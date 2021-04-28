import importlib


_surfaces = {
    "cairo": "blackrenderer.backends.cairo.CairoPixelSurface",
    "coregraphics": "blackrenderer.backends.coregraphics.CoreGraphicsPixelSurface",
    "skia": "blackrenderer.backends.skia.SkiaPixelSurface",
    "svg": "blackrenderer.backends.svg.SVGSurface",
}


def getSurface(name):
    fqName = _surfaces[name]
    moduleName, className = fqName.rsplit(".", 1)
    try:
        module = importlib.import_module(moduleName)
    except ImportError:
        return None
    return getattr(module, className)
