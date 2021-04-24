import sys
from blackrenderer.colrFont import COLRFont
from blackrenderer.backendSkia import PixelSurface, SkiaBackend


font = COLRFont(sys.argv[1])
glyphName = sys.argv[2]

minX, minY, maxX, maxY = font.getGlyphBounds(glyphName)

surface = PixelSurface(minX, minY, maxX - minX, maxY - minY)
backend = SkiaBackend(surface.canvas)
print(font.keys())

font.drawGlyph(sys.argv[2], backend)

surface.saveImage(f"{glyphName}.png")
