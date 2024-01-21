#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter_kicad_pretty.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import time

import exporter


# Default precision for :g format is 6
class Converter:
    def __init__(self, model_path, model_type='wrl'):
        if model_type not in ('wrl', 'x3d'):
            raise Exception()
        self.model_path = model_path
        self.model_type = model_type

    @staticmethod
    def layers_to_text(mask):
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

        return ' '.join(layers)

    @staticmethod
    def pad_style_to_text(value):
        styles = {
            exporter.AbstractPad.STYLE_CIRCLE: 'circle',
            exporter.AbstractPad.STYLE_RECT: 'rect',
            exporter.AbstractPad.STYLE_OVAL: 'oval',
            exporter.AbstractPad.STYLE_TRAPEZOID: 'trapezoid'}
        return styles[value]

    @staticmethod
    def pad_type_to_text(value):
        types = {
            exporter.AbstractPad.FAMILY_SMD: 'smd',
            exporter.AbstractPad.FAMILY_TH: 'thru_hole',
            exporter.AbstractPad.FAMILY_NPTH: 'np_thru_hole',
            exporter.AbstractPad.FAMILY_CONNECT: 'connect'}
        return types[value]

    @staticmethod
    def get_module_type_str(objects):
        family = exporter.AbstractPad.FAMILY_SMD
        for pad in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            if pad.family != exporter.AbstractPad.FAMILY_SMD:
                family = exporter.AbstractPad.FAMILY_TH
                break

        if family == exporter.AbstractPad.FAMILY_TH:
            return 'through_hole'
        else:
            return 'smd'

    def circle_to_text(self, circle):
        if circle.part is not None:
            # Arc
            angle = circle.part[0] * math.pi / 180.0
            start = (circle.position[0] + math.cos(angle) * circle.radius,
                     circle.position[1] + math.sin(angle) * circle.radius)
            rotation = abs(circle.part[1] - circle.part[0])

            out = '  (fp_arc'
            out += f' (start {circle.position[0]:g} {circle.position[1]:g})'
            out += f' (end {start[0]:g} {start[1]:g})'
            out += f' (angle {rotation:g})'
        else:
            # Circle
            out = '  (fp_circle'
            out += f' (center {circle.position[0]:g} {circle.position[1]:g})'
            out += f' (end {circle.position[0]:g} {circle.position[1] + circle.radius:g})'

        out += ' (layer {:s})'.format(Converter.layers_to_text(circle.layer))
        out += f' (width {circle.thickness:g})'
        out += ')\n'
        return out

    def label_to_text(self, label):
        if label is None:
            return ''

        out = '  (fp_text reference REF (at {:g} {:g}) (layer {:s})\n'.format(
            *label.position, Converter.layers_to_text(label.layer))
        out += '    (effects (font (size {:g} {:g}) (thickness {:g})))\n'.format(
            label.font, label.font, label.thickness)
        out += '  )\n'
        out += '  (fp_text value {:s} (at {:g} {:g}) (layer F.Fab)\n'.format(
            label.name, *label.position)
        out += '    (effects (font (size {:g} {:g}) (thickness {:g})))\n'.format(
            label.font, label.font, label.thickness)
        out += '  )\n'
        return out

    def string_to_text(self, string):
        out = '  (fp_text user {:s} (at {:g} {:g}) (layer {:s})\n'.format(
            string.value, *string.position, Converter.layers_to_text(string.layer))
        out += '    (effects (font (size {:g} {:g}) (thickness {:g})))\n'.format(
            string.font, string.font, string.thickness)
        out += '  )\n'
        return out

    def line_to_text(self, line):
        return '  (fp_line (start {:g} {:g}) (end {:g} {:g}) (layer {:s}) (width {:g}))\n'.format(
            *line.start, *line.end, Converter.layers_to_text(line.layer), line.thickness)

    def rect_to_text(self, rect):
        return ''.join([self.line_to_text(line) for line in rect.lines])

    def pad_to_text(self, pad):
        pad_name = str(pad.number) if len(str(pad.number)) > 0 else '""'

        out = f'  (pad {pad_name}'
        out += ' {:s} {:s}'.format(Converter.pad_type_to_text(pad.family),
            Converter.pad_style_to_text(pad.style))
        out += f' (at {pad.position[0]:g} {pad.position[1]:g})'
        out += f' (size {pad.size[0]:g} {pad.size[1]:g})'
        if pad.family in (exporter.AbstractPad.FAMILY_TH, exporter.AbstractPad.FAMILY_NPTH):
            if pad.style == exporter.AbstractPad.STYLE_OVAL:
                out += f' (drill oval {pad.diameter[0]:g} {pad.diameter[1]:g})'
            else:
                out += f' (drill {pad.diameter:g})'
        out += ' (layers {:s})'.format(Converter.layers_to_text(pad.copper | pad.mask | pad.paste))
        out += ')\n'
        return out

    def poly_to_text(self, poly):
        out = '  (fp_poly (pts'
        for vertex in poly.vertices:
            out += f' (xy {vertex[0]:g} {vertex[1]:g})'
        out += ') (layer {:s}) (width {:g}))\n'.format(Converter.layers_to_text(poly.layer),
            poly.thickness)
        return out

    def footprint_to_text(self, footprint):
        objects = footprint.generate()
        timestamp = time.time()

        out = f'(module {footprint.name} (layer F.Cu) (tedit {int(timestamp):08X})\n'

        out += '  (attr {:s})\n'.format(self.get_module_type_str(objects))
        if footprint.description is not None:
            out += f'  (descr "{footprint.description}")\n'

        for obj in filter(lambda x: isinstance(x, exporter.Label), objects):
            out += self.label_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.String), objects):
            out += self.string_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Circle), objects):
            out += self.circle_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Line), objects):
            out += self.line_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Rect), objects):
            out += self.rect_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Poly), objects):
            out += self.poly_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            out += self.pad_to_text(obj)

        out += f'  (model {self.model_path}/{footprint.model}.{self.model_type}\n'
        out += '    (at (xyz 0 0 0))\n'
        out += '    (scale (xyz 1 1 1))\n'
        out += '    (rotate (xyz 0 0 0))\n'
        out += '  )\n'

        out += ')\n'
        return out

    def generate(self, part):
        return self.footprint_to_text(part)
