#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import functools
import hashlib
import math
import numpy

def make_vector(data, size=None):
    if data is None:
        return None

    if isinstance(data, (tuple, list)):
        if any(not isinstance(axis, float) for axis in data):
            raise ValueError()
    elif not isinstance(data, numpy.ndarray):
        raise TypeError()

    if isinstance(size, tuple):
        if len(data) not in size:
            return IndexError()
    elif size is not None:
        if len(data) != size:
            return IndexError()

    if isinstance(data, numpy.ndarray):
        return tuple(data.tolist())
    if isinstance(data, list):
        return tuple(data)
    return data


class Layer:
    # Default layer numbers
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

    # Layers unused by old KiCad
    FAB         = 32

    def __init__(self, mask=0):
        self.mask = mask

    def __add__(self, other):
        result = Layer()
        if isinstance(other, Layer):
            result.mask = self.mask | other.mask
        else:
            result.mask = self.mask | Layer.to_mask(other).mask
        return result

    def layers(self):
        layers = [getattr(Layer, attribute) for attribute in dir(Layer) \
            if not attribute.startswith('__') and isinstance(getattr(Layer, attribute), int)]
        result = []

        for i in layers:
            if self.mask & (1 << i):
                result.append(i)
        if len(result) == 0:
            return None
        if len(result) == 1:
            return result[0]
        return tuple(result)

    @staticmethod
    def to_mask(layer):
        result = 0

        if isinstance(layer, int):
            result = 1 << layer
        else:
            for i in layer:
                result |= 1 << i

        return Layer(result)


class Circle:
    def __init__(self, position, radius, thickness, part=None, layer=Layer.SILK_FRONT):
        if not isinstance(radius, float):
            raise TypeError()
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()

        self.position = make_vector(position)
        self.part = make_vector(part)

        self.radius = radius
        self.thickness = thickness
        self.layer = Layer.to_mask(layer)

    def __hash__(self):
        return hash((self.position, self.radius, self.thickness, self.part, self.layer))


class Label:
    def __init__(self, text, position, thickness, font, layer=Layer.SILK_FRONT):
        if not isinstance(text, str):
            raise TypeError()
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(font, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()

        self.position = make_vector(position)

        self.text = text
        self.font = font
        self.thickness = thickness
        self.layer = Layer.to_mask(layer)

    def __hash__(self):
        return hash((
            self.position,
            int(hashlib.md5(self.text.encode()).hexdigest(), 16),
            self.font,
            self.thickness,
            self.layer
        ))


class String:
    def __init__(self, text, position, thickness, font, layer=Layer.SILK_FRONT,
                 name='', hidden=False):
        if not isinstance(text, str):
            raise TypeError()
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(font, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()
        if not isinstance(name, str):
            raise TypeError()
        if not isinstance(hidden, bool):
            raise TypeError()

        position_converted = make_vector(position)
        self.position = (position_converted[0], position_converted[1], 0.0)

        self.text = text
        self.font = font
        self.thickness = thickness
        self.layer = Layer.to_mask(layer)
        self.name = name
        self.hidden = hidden

    def __hash__(self):
        return hash((
            self.position,
            int(hashlib.md5(self.text.encode()).hexdigest(), 16),
            self.font,
            self.thickness,
            self.layer,
            int(hashlib.md5(self.name.encode()).hexdigest(), 16),
            self.hidden
        ))


class Line:
    def __init__(self, start, end, thickness, layer=Layer.SILK_FRONT):
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()

        self.start = make_vector(start)
        self.end = make_vector(end)

        self.thickness = thickness
        self.layer = Layer.to_mask(layer)

    def __hash__(self):
        return hash((self.start, self.end, self.thickness, self.layer))


class Rect:
    def __init__(self, top, bottom, thickness, layer=Layer.SILK_FRONT):
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()

        top_converted = make_vector(top)
        bot_converted = make_vector(bottom)

        self.lines = (
            Line((top_converted[0], bot_converted[1]), (bot_converted[0], bot_converted[1]),
                 thickness, layer),
            Line((top_converted[0], top_converted[1]), (top_converted[0], bot_converted[1]),
                 thickness, layer),
            Line((top_converted[0], top_converted[1]), (bot_converted[0], top_converted[1]),
                 thickness, layer),
            Line((bot_converted[0], top_converted[1]), (bot_converted[0], bot_converted[1]),
                 thickness, layer)
        )

    def __hash__(self):
        return hash(self.lines)


class AbstractPad:
    FAMILY_SMD, FAMILY_TH, FAMILY_NPTH, FAMILY_CONNECT = range(0, 4)
    LAYERS_NONE, LAYERS_FRONT, LAYERS_BACK, LAYERS_BOTH = range(0, 4)
    STYLE_CIRCLE, STYLE_RECT, STYLE_OVAL, STYLE_TRAPEZOID = range(0, 4)

    def __init__(self, text, size, position, diameter, style, family, copper, paste):
        if not isinstance(text, str):
            raise TypeError()
        if not isinstance(style, int):
            raise TypeError()
        if not isinstance(family, int):
            raise TypeError()
        if not isinstance(copper, int):
            raise TypeError()
        if not isinstance(paste, int):
            raise TypeError()

        self.size = make_vector(size)
        self.position = make_vector(position)
        self.diameter = diameter if isinstance(diameter, float) else make_vector(diameter)

        self.text = text
        self.style = style
        self.family = family

        self.copper = Layer()
        self.mask = Layer()
        self.paste = Layer()

        if self.family == AbstractPad.FAMILY_SMD:
            if copper == AbstractPad.LAYERS_FRONT:
                self.copper += Layer.CU_FRONT
                self.mask += Layer.MASK_FRONT
            elif copper == AbstractPad.LAYERS_BACK:
                self.copper += Layer.CU_BACK
                self.mask += Layer.MASK_BACK
            else:
                raise ValueError() # Configuration unsupported
        else:
            if copper == AbstractPad.LAYERS_BOTH:
                self.copper += (Layer.CU_BACK, Layer.CU_FRONT)
            elif copper != AbstractPad.LAYERS_NONE:
                raise ValueError() # Configuration unsupported
            self.mask += (Layer.MASK_FRONT, Layer.MASK_BACK)

        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_FRONT):
            self.paste += Layer.PASTE_FRONT
        if paste in (AbstractPad.LAYERS_BOTH, AbstractPad.LAYERS_BACK):
            self.paste += Layer.PASTE_BACK

    def __hash__(self):
        return hash((
            int(hashlib.md5(self.text.encode()).hexdigest(), 16),
            self.size,
            self.position,
            self.diameter,
            self.style,
            self.family,
            self.copper,
            self.mask,
            self.paste
        ))


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
        self.size = make_vector(size)
        self.position = make_vector(position)

    def __hash__(self):
        return hash((self.size, self.position))


class Poly:
    LAYER_COPPER, LAYER_SILK = range(0, 2)

    def __init__(self, vertices, thickness, layer):
        if not isinstance(vertices, (tuple, list)):
            raise TypeError()
        if not isinstance(thickness, float):
            raise TypeError()
        if not isinstance(layer, int):
            raise TypeError()

        self.vertices = [make_vector(vertex) for vertex in vertices]
        self.thickness = thickness
        self.layer = Layer.to_mask(layer)

    def __hash__(self):
        return hash((*self.vertices, self.thickness, self.layer))


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
