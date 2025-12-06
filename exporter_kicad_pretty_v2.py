#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter_kicad_pretty_v2.py
# Copyright (C) 2025 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import uuid
import numpy as np

import exporter


# Default precision for :g format is 6
class Converter:
    GENERATOR = 'kmodgen'
    GENERATOR_VERSION = '9.0'
    VERSION = '20241229'
    UUID_PREFIX = ''
    UUID_SEQUENCE = 0

    def __init__(self, model_path, model_type='wrl'):
        if model_type not in ('wrl', 'x3d'):
            raise KeyError()
        self.model_path = model_path
        self.model_type = model_type

    @staticmethod
    def layers_to_text(layer):
        if not isinstance(layer, exporter.Layer):
            raise TypeError()

        mask = layer.mask
        layers = []

        if mask & (1 << exporter.Layer.CU_BACK) and mask & (1 << exporter.Layer.CU_FRONT):
            layers.append('*.Cu')
        elif mask & (1 << exporter.Layer.CU_BACK):
            layers.append('B.Cu')
        elif mask & (1 << exporter.Layer.CU_FRONT):
            layers.append('F.Cu')

        if mask & (1 << exporter.Layer.PASTE_BACK) and mask & (1 << exporter.Layer.PASTE_FRONT):
            layers.append('*.Paste')
        elif mask & (1 << exporter.Layer.PASTE_BACK):
            layers.append('B.Paste')
        elif mask & (1 << exporter.Layer.PASTE_FRONT):
            layers.append('F.Paste')

        if mask & (1 << exporter.Layer.MASK_BACK) and mask & (1 << exporter.Layer.MASK_FRONT):
            layers.append('*.Mask')
        elif mask & (1 << exporter.Layer.MASK_BACK):
            layers.append('B.Mask')
        elif mask & (1 << exporter.Layer.MASK_FRONT):
            layers.append('F.Mask')

        if mask & (1 << exporter.Layer.SILK_BACK) and mask & (1 << exporter.Layer.SILK_FRONT):
            layers.append('*.SilkS')
        elif mask & (1 << exporter.Layer.SILK_BACK):
            layers.append('B.SilkS')
        elif mask & (1 << exporter.Layer.SILK_FRONT):
            layers.append('F.SilkS')

        if mask & (1 << exporter.Layer.FAB):
            layers.append('F.Fab')

        return ' '.join([f'"{layer}"' for layer in layers])

    @staticmethod
    def make_uuid():
        out = str(uuid.uuid3(uuid.NAMESPACE_DNS,
                             f'{Converter.UUID_PREFIX}:{Converter.UUID_SEQUENCE}'))
        Converter.UUID_SEQUENCE += 1
        return out

    @staticmethod
    def reset_uuid(name, digest):
        Converter.UUID_SEQUENCE = 0
        Converter.UUID_PREFIX = f'{name}:{digest}'

    @staticmethod
    def pad_style_to_text(value):
        styles = {
            exporter.AbstractPad.STYLE_CIRCLE: 'circle',
            exporter.AbstractPad.STYLE_RECT: 'rect',
            exporter.AbstractPad.STYLE_OVAL: 'oval',
            exporter.AbstractPad.STYLE_TRAPEZOID: 'trapezoid'
        }
        return styles[value]

    @staticmethod
    def pad_type_to_text(value):
        types = {
            exporter.AbstractPad.FAMILY_SMD: 'smd',
            exporter.AbstractPad.FAMILY_TH: 'thru_hole',
            exporter.AbstractPad.FAMILY_NPTH: 'np_thru_hole',
            exporter.AbstractPad.FAMILY_CONNECT: 'connect'
        }
        return types[value]

    @staticmethod
    def get_module_type_str(objects):
        family = exporter.AbstractPad.FAMILY_SMD
        for pad in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            if pad.family == exporter.AbstractPad.FAMILY_TH:
                family = pad.family
                break

        if family == exporter.AbstractPad.FAMILY_TH:
            return 'through_hole'
        return 'smd'

    @staticmethod
    def circle_to_text(circle):
        if circle.part is not None:
            # Arc
            rotation = abs(circle.part[1] - circle.part[0])
            beg_angle = np.deg2rad(circle.part[0])
            mid_angle = np.deg2rad(circle.part[0] + rotation / 2.0)
            end_angle = np.deg2rad(circle.part[1])

            beg = (circle.position[0] + math.cos(beg_angle) * circle.radius,
                   circle.position[1] + math.sin(beg_angle) * circle.radius)
            mid = (circle.position[0] + math.cos(mid_angle) * circle.radius,
                   circle.position[1] + math.sin(mid_angle) * circle.radius)
            end = (circle.position[0] + math.cos(end_angle) * circle.radius,
                   circle.position[1] + math.sin(end_angle) * circle.radius)

            out = '\t(fp_arc\n'
            out += f'\t\t(start {round(beg[0], 6):g} {round(beg[1], 6):g})\n'
            out += f'\t\t(mid {round(mid[0], 6):g} {round(mid[1], 6):g})\n'
            out += f'\t\t(end {round(end[0], 6):g} {round(end[1], 6):g})\n'
        else:
            # Circle
            out = '\t(fp_circle\n'
            out += f'\t\t(center {circle.position[0]:g} {circle.position[1]:g})\n'
            out += f'\t\t(end {circle.position[0]:g} {circle.position[1] + circle.radius:g})\n'

        out += '\t\t(stroke\n'
        out += f'\t\t\t(width {circle.thickness:g})\n'
        out += '\t\t\t(type solid)\n' # TODO Non-solid line types
        out += '\t\t)\n'

        if circle.closed:
            out += f'\t\t(fill {'yes' if circle.fill else 'no'})\n'

        out += f'\t\t(layer {Converter.layers_to_text(circle.layer)})\n'
        out += f'\t\t(uuid "{Converter.make_uuid()}")\n'
        out += '\t)\n'
        return out

    @staticmethod
    def label_to_text(label):
        if label is None:
            return ''

        out = ''
        out += Converter.string_to_text(exporter.String('REF', label.position, label.thickness,
            label.font, 'Reference', label.layer.layers(), False))
        out += Converter.string_to_text(exporter.String(label.text, label.position, label.thickness,
            label.font, 'Value', exporter.Layer.FAB, False))
        out += Converter.string_to_text(exporter.String('', label.position, label.thickness,
            label.font, 'Datasheet', exporter.Layer.FAB, True))
        out += Converter.string_to_text(exporter.String('', label.position, label.thickness,
            label.font, 'Description', exporter.Layer.FAB, True))
        return out

    @staticmethod
    def string_to_text(string):
        out = f'\t(property "{string.name}" "{string.text}"\n'
        out += f'\t\t(at {string.position[0]:g} {string.position[1]:g} {string.position[2]:g})\n'
        out += f'\t\t(layer {Converter.layers_to_text(string.layer)})\n'
        if string.hidden:
            out += '\t\t(hide yes)\n'
        out += f'\t\t(uuid "{Converter.make_uuid()}")\n'
        out += '\t\t(effects\n'
        out += '\t\t\t(font\n'
        out += f'\t\t\t\t(size {string.font:g} {string.font:g})\n'
        out += f'\t\t\t\t(thickness {string.thickness:g})\n'
        out += '\t\t\t)\n'
        out += '\t\t)\n'
        out += '\t)\n'
        return out

    @staticmethod
    def line_to_text(line):
        out = '\t(fp_line\n'
        out += f'\t\t(start {line.start[0]:g} {line.start[1]:g})\n'
        out += f'\t\t(end {line.end[0]:g} {line.end[1]:g})\n'
        out += '\t\t(stroke\n'
        out += f'\t\t\t(width {line.thickness:g})\n'
        out += '\t\t\t(type solid)\n' # TODO Non-solid line types
        out += '\t\t)\n'
        out += f'\t\t(layer {Converter.layers_to_text(line.layer)})\n'
        out += f'\t\t(uuid "{Converter.make_uuid()}")\n'
        out += '\t)\n'
        return out

    @staticmethod
    def rect_to_text(rect):
        return ''.join([Converter.line_to_text(line) for line in rect.lines])

    @staticmethod
    def pad_to_text(pad):
        out = f'\t(pad "{pad.text}"'
        out += f' {Converter.pad_type_to_text(pad.family)}'
        out += f' {Converter.pad_style_to_text(pad.style)}\n'

        out += f'\t\t(at {pad.position[0]:g} {pad.position[1]:g})\n'
        out += f'\t\t(size {pad.size[0]:g} {pad.size[1]:g})\n'

        if pad.family in (exporter.AbstractPad.FAMILY_TH, exporter.AbstractPad.FAMILY_NPTH):
            if pad.style == exporter.AbstractPad.STYLE_OVAL:
                out += f'\t\t(drill oval {pad.diameter[0]:g} {pad.diameter[1]:g})\n'
            else:
                out += f'\t\t(drill {pad.diameter:g})\n'

        out += f'\t\t(layers {Converter.layers_to_text(pad.copper + pad.mask + pad.paste)})\n'

        if pad.family == exporter.AbstractPad.FAMILY_TH:
            out += '\t\t(remove_unused_layers no)\n'

        out += f'\t\t(uuid "{Converter.make_uuid()}")\n'
        out += '\t)\n'
        return out

    @staticmethod
    def poly_to_text(poly):
        out = '\t(fp_poly\n'
        out += '\t\t(pts\n'

        out += '\t\t\t'
        out += ' '.join([f'(xy {vertex[0]:g} {vertex[1]:g})' for vertex in poly.vertices])
        out += '\n'
        out += '\t\t)\n'

        out += '\t\t(stroke\n'
        out += f'\t\t\t(width {poly.thickness:g})\n'
        out += '\t\t\t(type solid)\n' # TODO Non-solid line types
        out += '\t\t)\n'

        out += f'\t\t(fill {'yes' if poly.fill else 'no'})\n'
        out += f'\t\t(layer {Converter.layers_to_text(poly.layer)})\n'
        out += f'\t\t(uuid "{Converter.make_uuid()}")\n'
        out += '\t)\n'
        return out

    def footprint_to_text(self, footprint):
        objects = footprint.generate()
        footprint_hash = hash(tuple(objects))
        footprint_layer = exporter.Layer.to_mask(exporter.Layer.CU_FRONT)
        Converter.reset_uuid(footprint.name, footprint_hash)

        out = f'(footprint "{footprint.name}"\n'
        out += f'\t(version {Converter.VERSION})\n'
        out += f'\t(generator "{Converter.GENERATOR}")\n'
        out += f'\t(generator_version "{Converter.GENERATOR_VERSION}")\n'
        out += f'\t(layer {Converter.layers_to_text(footprint_layer)})\n'
        if footprint.description is not None:
            out += f'\t(descr "{footprint.description}")\n'

        for obj in filter(lambda x: isinstance(x, exporter.Label), objects):
            out += Converter.label_to_text(obj)

        out += f'\t(attr {self.get_module_type_str(objects)})\n'

        for obj in filter(lambda x: isinstance(x, exporter.String), objects):
            out += Converter.string_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Line), objects):
            out += Converter.line_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Rect), objects):
            out += Converter.rect_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Circle), objects):
            out += Converter.circle_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Poly), objects):
            out += Converter.poly_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            out += Converter.pad_to_text(obj)

        # Fonts
        out += '\t(embedded_fonts no)\n'

        # 3D model
        out += f'\t(model "{self.model_path}/{footprint.model}.{self.model_type}"\n'
        out += '\t\t(offset\n'
        out += '\t\t\t(xyz 0 0 0)\n'
        out += '\t\t)\n'
        out += '\t\t(scale\n'
        out += '\t\t\t(xyz 1 1 1)\n'
        out += '\t\t)\n'
        out += '\t\t(rotate\n'
        out += '\t\t\t(xyz 0 0 0)\n'
        out += '\t\t)\n'
        out += '\t)\n'

        out += ')\n'
        return out

    def generate(self, part):
        return self.footprint_to_text(part)
