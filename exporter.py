#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import functools
import math


class Circle:
    def __init__(self, position, radius, thickness, part=None):
        self.position = position
        self.radius = radius
        self.thickness = thickness
        self.part = part


class Label:
    def __init__(self, name, position, thickness, font):
        self.position = position
        self.name = name
        self.font = font
        self.thickness = thickness


class String:
    def __init__(self, value, position, thickness, font):
        self.position = position
        self.value = value
        self.font = font
        self.thickness = thickness


class Line:
    def __init__(self, start, end, thickness):
        self.start = start
        self.end = end
        self.thickness = thickness


class AbstractPad:
    class Layer:
        CU_BACK     = 0
        CU_FRONT    = 15
        ADHES_BACK  = 16
        ADHES_FRONT = 17
        PASTE_BACK  = 18
        PASTE_FRONT = 19
        SILK_BACK   = 20
        SILK_FRONT  = 21
        MASK_BACK   = 22
        MASK_FRONT  = 23
        DRAWINGS    = 24
        COMMENTS    = 25
        ECO1        = 26
        ECO2        = 27
        EDGES       = 28

    FAMILY_SMD, FAMILY_TH, FAMILY_NPTH, FAMILY_CONNECT = range(0, 4)
    LAYERS_NONE, LAYERS_FRONT, LAYERS_BACK, LAYERS_BOTH = range(0, 4)
    STYLE_CIRCLE, STYLE_RECT, STYLE_OVAL, STYLE_TRAPEZOID = range(0, 4)

    def __init__(self, number, size, position, diameter, style, family, copper, paste):
        self.number = number
        self.size = size
        self.position = position
        self.diameter = diameter
        self.style = style
        self.family = family

        self.copper = 0
        self.mask = 0
        if self.family == AbstractPad.FAMILY_SMD:
            if copper == AbstractPad.LAYERS_FRONT:
                self.copper |= 1 << AbstractPad.Layer.CU_FRONT
                self.mask |= 1 << AbstractPad.Layer.MASK_FRONT
            elif copper == AbstractPad.LAYERS_BACK:
                self.copper |= 1 << AbstractPad.Layer.CU_BACK
                self.mask |= 1 << AbstractPad.Layer.MASK_BACK
            else:
                raise Exception() # Configuration unsupported
        else:
            if copper == AbstractPad.LAYERS_BOTH:
                self.copper |= 1 << AbstractPad.Layer.CU_BACK | 1 << AbstractPad.Layer.CU_FRONT
            elif copper != AbstractPad.LAYERS_NONE:
                raise Exception() # Configuration unsupported
            self.mask |= (1 << AbstractPad.Layer.MASK_FRONT) | (1 << AbstractPad.Layer.MASK_BACK)

        self.paste = 0
        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_FRONT):
            self.paste |= 1 << AbstractPad.Layer.PASTE_FRONT
        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_BACK):
            self.paste |= 1 << AbstractPad.Layer.PASTE_BACK


class HolePad(AbstractPad):
    def __init__(self, number, size, position, diameter, style=AbstractPad.STYLE_CIRCLE):
        AbstractPad.__init__(self, number, size, position, diameter, style, AbstractPad.FAMILY_TH,
                AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_NONE)


class SmdPad(AbstractPad):
    def __init__(self, number, size, position):
        AbstractPad.__init__(self, number, size, position, 0.0, AbstractPad.STYLE_RECT, AbstractPad.FAMILY_SMD,
                AbstractPad.LAYERS_FRONT, AbstractPad.LAYERS_FRONT)


class Poly:
    LAYER_COPPER, LAYER_SILK = range(0, 2)

    def __init__(self, vertices, thickness, layer):
        self.vertices = vertices
        self.thickness = thickness
        self.layer = 1 << layer


class Footprint:
    def __init__(self, name, description, model=None):
        self.name = name
        self.description = None if description is None or description == '' else description
        self.model = name if model is None else model


def collideLine(line, pads, thickness, gap):
    minWidth = thickness

    def pointInRect(rect, point):
        epsilon = 1e-6
        inRange = lambda x, start, end: start - epsilon <= x <= end + epsilon
        return inRange(point[0], rect[0][0], rect[1][0]) and inRange(point[1], rect[0][1], rect[1][1])

    def getCrossPoint(line1, line2):
        epsilon = 1e-6
        det = line1[0] * line2[1] - line1[1] * line2[0]
        if abs(det) > epsilon:
            dx = -line1[2] * line2[1] + line1[1] * line2[2]
            dy = -line1[0] * line2[2] + line1[2] * line2[0]
            return (dx / det, dy / det)
        else:
            return None

    def getLineFunc(start, end):
        # Returns (A, B, C)
        dx, dy = end[0] - start[0], end[1] - start[1]

        if dx == 0.0:
            return (1.0, 0.0, -start[0])
        elif dy == 0.0:
            return (0.0, 1.0, -start[1])
        else:
            return (dy, -dx, dx * start[1] - dy * start[0])

    def getCrossSegment(line, segment, box):
        start, end = segment[0], segment[1]
        crossPoint = getCrossPoint(line, getLineFunc(start, end))
        if crossPoint is None:
            return None
        rect = ((min(start[0], end[0]), min(start[1], end[1])), (max(start[0], end[0]), max(start[1], end[1])))
        return crossPoint if pointInRect(rect, crossPoint) and pointInRect(box, crossPoint) else None

    def getPadSegments(pad):
        segments = []
        pos, offset = pad.position, (pad.size[0] / 2., pad.size[1] / 2.)
        segments.append(((pos[0] - offset[0], pos[1] - offset[1]), (pos[0] - offset[0], pos[1] + offset[1])))
        segments.append(((pos[0] + offset[0], pos[1] - offset[1]), (pos[0] + offset[0], pos[1] + offset[1])))
        segments.append(((pos[0] - offset[0], pos[1] - offset[1]), (pos[0] + offset[0], pos[1] - offset[1])))
        segments.append(((pos[0] - offset[0], pos[1] + offset[1]), (pos[0] + offset[0], pos[1] + offset[1])))
        return segments

    def shrinkLine(line, shrinkStart, shrinkEnd, value):
        length = math.sqrt(math.pow(line[1][0] - line[0][0], 2.0) + math.pow(line[1][1] - line[0][1], 2.0))
        kx, ky = (line[1][0] - line[0][0]) / length, (line[1][1] - line[0][1]) / length
        start, end = line[0], line[1]
        initialAngle = math.atan2(end[1] - start[1], end[0] - start[0])
        if shrinkStart:
            start = (start[0] + kx * value, start[1] + ky * value)
        if shrinkEnd:
            end = (end[0] - kx * value, end[1] - ky * value)
        resultAngle = math.atan2(end[1] - start[1], end[0] - start[0])
        if abs(resultAngle - initialAngle) > math.pi / 2.:
            return None
        else:
            return (start, end)

    def checkPointCollisions(point, pads):
        padRectFunc = lambda pad: ((pad.position[0] - pad.size[0] / 2., pad.position[1] - pad.size[1] / 2.),
                (pad.position[0] + pad.size[0] / 2., pad.position[1] + pad.size[1] / 2.))
        collisions = [pointInRect(padRectFunc(pad), point) for pad in pads]
        return functools.reduce(lambda x, y: x or y, collisions)

    def checkChunkCollisions(chunk, pads):
        collisionFunc = lambda x: checkPointCollisions(chunk[0], [x]) and checkPointCollisions(chunk[1], [x])
        collisions = [collisionFunc(pad) for pad in pads]
        return functools.reduce(lambda x, y: x or y, collisions)

    if len(pads) == 0:
        return [line]

    # Create common line function Ax + By + C = 0
    lineBox = ((min(line.start[0], line.end[0]), min(line.start[1], line.end[1])),
            (max(line.start[0], line.end[0]), max(line.start[1], line.end[1])))
    lineFunc = getLineFunc(line.start, line.end)
    segFunc = lambda x: getCrossSegment(lineFunc, x, lineBox)

    # Subdivide all pads into segments
    segments = []
    [segments.extend(getPadSegments(pad)) for pad in pads]

    # Generate crossing points for the given line
    crosses = [line.start, line.end]
    crosses.extend([cross for cross in [segFunc(seg) for seg in segments] if cross is not None])

    # Sort crossing points
    distFunc = lambda x: math.sqrt(math.pow(x[0] - line.start[0], 2.0) + math.pow(x[1] - line.start[1], 2.0))
    crosses = sorted(crosses, key=distFunc)

    # Generate chunks
    chunks = []
    for i in range(0, len(crosses) - 1):
        chunks.append((crosses[i], crosses[i + 1]))
    # Filter chunks by length
    chunkLengthFunc = lambda x: math.sqrt(math.pow(x[1][0] - x[0][0], 2.0) + math.pow(x[1][1] - x[0][1], 2.0))
    chunks = [chunk for chunk in chunks if chunkLengthFunc(chunk) >= minWidth]

    # Exclude chunks intersected with pads
    chunks = [chunk for chunk in chunks if not checkChunkCollisions(chunk, pads)]

    # Reduce line width
    chunkShrinkFunc = lambda x: shrinkLine(x, checkPointCollisions(x[0], pads), checkPointCollisions(x[1], pads),
            gap + thickness / 2)
    chunks = [chunkShrinkFunc(chunk) for chunk in chunks]

    # Remove broken and short lines
    chunks = [chunk for chunk in chunks if chunk is not None and chunkLengthFunc(chunk) >= minWidth]

    return [Line(chunk[0], chunk[1], thickness) for chunk in chunks]
