#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import functools
import math


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


class Circle:
    def __init__(self, position, radius, thickness, part=None, layer=Layer.SILK_FRONT):
        self.position = position
        self.radius = radius
        self.thickness = thickness
        self.part = part
        self.layer = 1 << layer


class Label:
    def __init__(self, name, position, thickness, font, layer=Layer.SILK_FRONT):
        self.position = position
        self.name = name
        self.font = font
        self.thickness = thickness
        self.layer = 1 << layer


class String:
    def __init__(self, value, position, thickness, font, layer=Layer.SILK_FRONT):
        self.position = position
        self.value = value
        self.font = font
        self.thickness = thickness
        self.layer = 1 << layer


class Line:
    def __init__(self, start, end, thickness, layer=Layer.SILK_FRONT):
        self.start = start
        self.end = end
        self.thickness = thickness
        self.layer = 1 << layer


class Rect:
    def __init__(self, top, bottom, thickness, layer=Layer.SILK_FRONT):
        self.lines = [
                Line((top[0], bottom[1]), (bottom[0], bottom[1]), thickness, layer),
                Line((top[0], top[1]), (top[0], bottom[1]), thickness, layer),
                Line((top[0], top[1]), (bottom[0], top[1]), thickness, layer),
                Line((bottom[0], top[1]), (bottom[0], bottom[1]), thickness, layer)
        ]


class AbstractPad:
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
                self.copper |= 1 << Layer.CU_FRONT
                self.mask |= 1 << Layer.MASK_FRONT
            elif copper == AbstractPad.LAYERS_BACK:
                self.copper |= 1 << Layer.CU_BACK
                self.mask |= 1 << Layer.MASK_BACK
            else:
                raise Exception() # Configuration unsupported
        else:
            if copper == AbstractPad.LAYERS_BOTH:
                self.copper |= 1 << Layer.CU_BACK | 1 << Layer.CU_FRONT
            elif copper != AbstractPad.LAYERS_NONE:
                raise Exception() # Configuration unsupported
            self.mask |= (1 << Layer.MASK_FRONT) | (1 << Layer.MASK_BACK)

        self.paste = 0
        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_FRONT):
            self.paste |= 1 << Layer.PASTE_FRONT
        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_BACK):
            self.paste |= 1 << Layer.PASTE_BACK


class HolePad(AbstractPad):
    def __init__(self, number, size, position, diameter, style=AbstractPad.STYLE_CIRCLE):
        super().__init__(number, size, position, diameter, style, AbstractPad.FAMILY_TH,
                         AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_NONE)


class SmdPad(AbstractPad):
    def __init__(self, number, size, position):
        super().__init__(number, size, position, 0.0, AbstractPad.STYLE_RECT,
                         AbstractPad.FAMILY_SMD, AbstractPad.LAYERS_FRONT, AbstractPad.LAYERS_FRONT)


class Cutout:
    def __init__(self, size, position):
        self.size = size
        self.position = position


class Poly:
    LAYER_COPPER, LAYER_SILK = range(0, 2)

    def __init__(self, vertices, thickness, layer):
        self.vertices = vertices
        self.thickness = thickness
        self.layer = 1 << layer


class Footprint:
    def __init__(self, name, description, model=None, spec=None):
        self.name = name
        self.description = None if description is None or description == '' else description
        self.model = name if model is None else model

        if spec is not None:
            self.font = spec['font']
            self.gap = spec['gap']
            self.thickness = spec['thickness']


def collide_line(line, pads, thickness, gap):
    min_width = thickness

    def point_in_rect(rect, point):
        epsilon = 1e-6
        in_range = lambda x, start, end: start - epsilon <= x <= end + epsilon
        if not in_range(point[0], rect[0][0], rect[1][0]):
            return False
        if not in_range(point[1], rect[0][1], rect[1][1]):
            return False
        return True

    def get_cross_point(line1, line2):
        epsilon = 1e-6
        det = line1[0] * line2[1] - line1[1] * line2[0]

        if abs(det) <= epsilon:
            return None

        delta_x = -line1[2] * line2[1] + line1[1] * line2[2]
        delta_y = -line1[0] * line2[2] + line1[2] * line2[0]
        return (delta_x / det, delta_y / det)

    def get_line_func(start, end):
        # Returns (A, B, C)
        delta_x, delta_y = end[0] - start[0], end[1] - start[1]

        if delta_x == 0.0:
            return (1.0, 0.0, -start[0])
        if delta_y == 0.0:
            return (0.0, 1.0, -start[1])
        return (delta_y, -delta_x, delta_x * start[1] - delta_y * start[0])

    def get_cross_segment(line, segment, box):
        start, end = segment[0], segment[1]

        cross_point = get_cross_point(line, get_line_func(start, end))
        if cross_point is None:
            return None

        rect = ((min(start[0], end[0]), min(start[1], end[1])),
                (max(start[0], end[0]), max(start[1], end[1])))
        if not point_in_rect(rect, cross_point) or not point_in_rect(box, cross_point):
            return None

        return cross_point

    def get_pad_segments(pad):
        segments = []
        pos, offset = pad.position, (pad.size[0] / 2.0, pad.size[1] / 2.0)
        segments.append(((pos[0] - offset[0], pos[1] - offset[1]),
            (pos[0] - offset[0], pos[1] + offset[1])))
        segments.append(((pos[0] + offset[0], pos[1] - offset[1]),
            (pos[0] + offset[0], pos[1] + offset[1])))
        segments.append(((pos[0] - offset[0], pos[1] - offset[1]),
            (pos[0] + offset[0], pos[1] - offset[1])))
        segments.append(((pos[0] - offset[0], pos[1] + offset[1]),
            (pos[0] + offset[0], pos[1] + offset[1])))
        return segments

    def shrink_line(line, shrink_start, shrink_end, value):
        length = math.sqrt(math.pow(line[1][0] - line[0][0], 2.0)
                           + math.pow(line[1][1] - line[0][1], 2.0))
        x_coef, y_coef = (line[1][0] - line[0][0]) / length, (line[1][1] - line[0][1]) / length
        start, end = line[0], line[1]
        src_angle = math.atan2(end[1] - start[1], end[0] - start[0])
        if shrink_start:
            start = (start[0] + x_coef * value, start[1] + y_coef * value)
        if shrink_end:
            end = (end[0] - x_coef * value, end[1] - y_coef * value)

        dst_angle = math.atan2(end[1] - start[1], end[0] - start[0])
        if abs(dst_angle - src_angle) > math.pi / 2.0:
            return None

        return (start, end)

    def pad_rect_func(pad):
        return ((pad.position[0] - pad.size[0] / 2.0, pad.position[1] - pad.size[1] / 2.0),
                (pad.position[0] + pad.size[0] / 2.0, pad.position[1] + pad.size[1] / 2.0))

    def check_point_collisions(point, pads):
        collisions = [point_in_rect(pad_rect_func(pad), point) for pad in pads]
        return functools.reduce(lambda x, y: x or y, collisions)

    def collision_func(chunk, pad):
        return check_point_collisions(chunk[0], [pad]) and check_point_collisions(chunk[1], [pad])

    def check_chunk_collisions(chunk, pads):
        collisions = [collision_func(chunk, pad) for pad in pads]
        return functools.reduce(lambda x, y: x or y, collisions)

    if len(pads) == 0:
        return [line]

    # Create common line function Ax + By + C = 0
    line_box = ((min(line.start[0], line.end[0]), min(line.start[1], line.end[1])),
        (max(line.start[0], line.end[0]), max(line.start[1], line.end[1])))
    line_func = get_line_func(line.start, line.end)
    seg_func = lambda x: get_cross_segment(line_func, x, line_box)

    # Subdivide all pads into segments
    segments = []
    for pad in pads:
        segments.extend(get_pad_segments(pad))

    # Generate crossing points for the given line
    crosses = [line.start, line.end]
    crosses.extend([cross for cross in [seg_func(seg) for seg in segments] if cross is not None])

    # Sort crossing points
    def dist_func(point):
        return math.sqrt(math.pow(point[0] - line.start[0], 2.0)
                         + math.pow(point[1] - line.start[1], 2.0))
    crosses = sorted(crosses, key=dist_func)

    # Generate chunks
    chunks = []
    for i in range(0, len(crosses) - 1):
        chunks.append((crosses[i], crosses[i + 1]))

    # Filter chunks by length
    def chunk_length(chunk):
        return math.sqrt(math.pow(chunk[1][0] - chunk[0][0], 2.0)
                         + math.pow(chunk[1][1] - chunk[0][1], 2.0))
    chunks = [chunk for chunk in chunks if chunk_length(chunk) >= min_width]

    # Exclude chunks intersected with pads
    chunks = [chunk for chunk in chunks if not check_chunk_collisions(chunk, pads)]

    # Reduce line width
    def shrink_chunk(chunk):
        return shrink_line(chunk,
            check_point_collisions(chunk[0], pads),
            check_point_collisions(chunk[1], pads),
            gap + thickness / 2)
    chunks = [shrink_chunk(chunk) for chunk in chunks]

    # Remove broken and short lines
    chunks = [chunk for chunk in chunks if chunk is not None and chunk_length(chunk) >= min_width]

    return [Line(chunk[0], chunk[1], thickness) for chunk in chunks]
