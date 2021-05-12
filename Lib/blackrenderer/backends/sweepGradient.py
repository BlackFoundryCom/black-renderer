from math import pi, ceil, sin, cos
from fontTools.misc.vector import Vector


def buildSweepGradientPatches(
    colorLine,
    center,
    radius,
    startAngle,
    endAngle,
    useGouraudShading,
):
    """Provides colorful patches that mimic a sweep gradient, for use, in
    particular, in the Cairo and CoreGraphics backends, since these libraries
    lack the sweep gradient feature."""
    patches = []
    # generate a fan of 'triangular' bezier patches, with center 'center' and radius 'radius'
    degToRad = pi / 180.0
    if useGouraudShading:
        maxAngle = pi / 360.0
        radius = 1.05 * radius  # we will use straight-edged triangles
    else:
        maxAngle = pi / 10.0
    n = len(colorLine)
    center = Vector(center)
    for i in range(n - 1):
        a0, col0 = colorLine[i + 0]
        a1, col1 = colorLine[i + 1]
        col0 = Vector(col0)
        col1 = Vector(col1)
        a0 = degToRad * (startAngle + a0 * (endAngle - startAngle))
        a1 = degToRad * (startAngle + a1 * (endAngle - startAngle))
        numSplits = int(ceil((a1 - a0) / maxAngle))
        p0 = Vector((cos(a0), sin(a0)))
        color0 = col0
        for a in range(numSplits):
            k = (a + 1.0) / numSplits
            angle1 = a0 + k * (a1 - a0)
            color1 = col0 + k * (col1 - col0)
            p1 = Vector((cos(angle1), sin(angle1)))
            P0 = center[0] + radius * p0[0], center[1] + radius * p0[1]
            P1 = center[0] + radius * p1[0], center[1] + radius * p1[1]
            # draw patch
            if useGouraudShading:
                patches.append(((P0, color0), (P1, color1)))
            else:
                # compute cubic Bezier antennas (control points) so as to approximate the circular arc p0-p1
                A = (p0 + p1).normalized()
                U = Vector((-A[1], A[0]))  # tangent to circle at A
                C0 = A + ((p0 - A).dot(p0) / U.dot(p0)) * U
                C1 = A + ((p1 - A).dot(p1) / U.dot(p1)) * U
                C0 = center + radius * (C0 + 0.33333 * (C0 - p0))
                C1 = center + radius * (C1 + 0.33333 * (C1 - p1))
                patches.append(((P0, color0), C0, C1, (P1, color1)))
            # move to next patch
            p0 = p1
            color0 = color1
    return patches
