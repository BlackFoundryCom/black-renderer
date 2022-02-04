try:
    from ._version import version as __version__
except ImportError:
    __version__ = "<unknown>"

# Optional command line arguments.
class BlackRendererSettings:
    fontSize = 250.0
    margin = 20.0
    useFontMetrics = False
    floatBbox = False
