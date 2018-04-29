#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter_kicad_pretty.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import time

import exporter


class Converter:
    def __init__(self, modelPath, modelType='wrl'):
        if modelType != 'wrl' and modelType != 'x3d':
            raise Exception()
        self.modelPath = modelPath
        self.modelType = modelType

    @staticmethod
    def layersToText(mask):
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
    def padStyleToText(padStyle):
        STYLES = {
                exporter.AbstractPad.STYLE_CIRCLE: 'circle',
                exporter.AbstractPad.STYLE_RECT: 'rect',
                exporter.AbstractPad.STYLE_OVAL: 'oval',
                exporter.AbstractPad.STYLE_TRAPEZOID: 'trapezoid'
        }
        return STYLES[padStyle]

    @staticmethod
    def padTypeToText(padType):
        TYPES = {
                exporter.AbstractPad.FAMILY_SMD: 'smd',
                exporter.AbstractPad.FAMILY_TH: 'thru_hole',
                exporter.AbstractPad.FAMILY_NPTH: 'np_thru_hole',
                exporter.AbstractPad.FAMILY_CONNECT: 'connect'
        }
        return TYPES[padType]

    def circleToText(self, circle):
        if circle.part is not None:
            # Arc
            angle = circle.part[0] * math.pi / 180.0
            start = (circle.position[0] + math.cos(angle) * circle.radius,
                    circle.position[1] + math.sin(angle) * circle.radius)
            rotation = abs(circle.part[1] - circle.part[0])
            return '  (fp_arc (start %.6f %.6f) (end %.6f %.6f) (angle %.6f) (layer F.SilkS) (width %.6f))\n'\
                    % (circle.position[0], circle.position[1], start[0], start[1], rotation, circle.thickness)
        else:
            # Circle
            return '  (fp_circle (center %.6f %.6f) (end %.6f %.6f) (layer F.SilkS) (width %.6f))\n'\
                    % (circle.position[0], circle.position[1], circle.position[0], circle.position[1] + circle.radius,
                            circle.thickness)

    def labelToText(self, label):
        if label is None:
            return ''

        out = ''
        out += '  (fp_text reference REF (at %.6f %.6f) (layer F.SilkS)\n' % (label.position[0], label.position[1])
        out += '    (effects (font (size %.6f %.6f) (thickness %.6f)))\n' % (label.font, label.font, label.thickness)
        out += '  )\n'
        out += '  (fp_text value %s (at %.6f %.6f) (layer F.Fab)\n'\
                % (label.name, label.position[0], label.position[1])
        out += '    (effects (font (size %.6f %.6f) (thickness %.6f)))\n' % (label.font, label.font, label.thickness)
        out += '  )\n'
        return out

    def stringToText(self, string):
        out = ''
        out += '  (fp_text user %s (at %.6f %.6f) (layer F.SilkS)\n'\
                % (string.value, string.position[0], string.position[1])
        out += '    (effects (font (size %.6f %.6f) (thickness %.6f)))\n'\
                % (string.font, string.font, string.thickness)
        out += '  )\n'
        return out

    def lineToText(self, line):
        return '  (fp_line (start %.6f %.6f) (end %.6f %.6f) (layer F.SilkS) (width %.6f))\n'\
                % (line.start[0], line.start[1], line.end[0], line.end[1], line.thickness)

    def rectToText(self, rect):
        return ''.join([self.lineToText(line) for line in rect.lines])

    def padToText(self, pad):
        padName = str(pad.number) if len(str(pad.number)) else '""'

        out = ''
        out += '  (pad %s' % padName
        out += ' %s %s' % (Converter.padTypeToText(pad.family), Converter.padStyleToText(pad.style))
        out += ' (at %.6f %.6f)' % (pad.position[0], pad.position[1])
        out += ' (size %.6f %.6f)' % (pad.size[0], pad.size[1])
        if pad.family == exporter.AbstractPad.FAMILY_TH or pad.family == exporter.AbstractPad.FAMILY_NPTH:
            out += ' (drill %.6f)' % pad.diameter
        out += ' (layers %s)' % Converter.layersToText(pad.copper | pad.mask | pad.paste)
        out += ')\n'
        return out

    def polyToText(self, poly):
        out = ''
        out += '  (fp_poly (pts'
        for vertex in poly.vertices:
            out += ' (xy %.6f %.6f)' % (vertex[0], vertex[1])
        out += ') (layer %s) (width 0.16))\n' % Converter.layersToText(poly.layer)
        return out

    def footprintToText(self, footprint):
        timestamp = time.time()

        out = '(module %s (layer F.Cu) (tedit %08X)\n' % (footprint.name, int(timestamp))

        if footprint.description is not None:
            out += '  (descr "%s")\n' % footprint.description

        objects = footprint.generate()

        for obj in filter(lambda x: isinstance(x, exporter.Label), objects):
            out += self.labelToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.String), objects):
            out += self.stringToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Circle), objects):
            out += self.circleToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Line), objects):
            out += self.lineToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Rect), objects):
            out += self.rectToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Poly), objects):
            out += self.polyToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            out += self.padToText(obj)

        out += '  (model %s%s.%s\n' % (self.modelPath, footprint.model, self.modelType)
        out += '    (at (xyz 0 0 0))\n'
        out += '    (scale (xyz 1 1 1))\n'
        out += '    (rotate (xyz 0 0 0))\n'
        out += '  )\n'

        out += ')\n'
        return out

    def generate(self, part):
        return self.footprintToText(part)
