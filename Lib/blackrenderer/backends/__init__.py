import importlib


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


def getSurfaceClass(name, imageExtension=None):
    fqName = _surfaces[imageExtension][name]
    moduleName, className = fqName.rsplit(".", 1)
    try:
        module = importlib.import_module(moduleName)
    except ModuleNotFoundError:
        return None
    return getattr(module, className)
