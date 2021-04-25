#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# exporter_kicad.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import datetime
import math
import re
import time

import exporter

class Converter:
    def __init__(self, model_path, library_path=None, library_name=None, model_type='wrl'):
        if model_type not in ('wrl', 'x3d'):
            raise Exception()
        self.model_path = model_path
        self.model_type = model_type
        self.library_path = library_path if library_name is not None else None
        self.library_name = library_name if library_path is not None else None

    def circle_to_text(self, circle):
        if circle.part is not None:
            # Arc
            angle = circle.part[0] * math.pi / 180.0
            start = (circle.position[0] + math.cos(angle) * circle.radius,
                     circle.position[1] + math.sin(angle) * circle.radius)
            return 'DA {:g} {:g} {:g} {:g} {:d} {:g} 21\n'.format(*circle.position, *start,
                int(abs(circle.part[1] - circle.part[0]) * 10.0), circle.thickness)

        # Circle
        return 'DC {:g} {:g} {:g} {:g} {:g} 21\n'.format(*circle.position,
            circle.position[0], circle.position[1] + circle.radius, circle.thickness)

    def label_to_text(self, label):
        if label is None:
            return ''

        out = ''
        out += 'T0 {:g} {:g} {:g} {:g} 0 {:g} N V 21 N "{:s}"\n'.format(*label.position,
            label.font, label.font, label.thickness, label.name)
        out += 'T1 {:g} {:g} {:g} {:g} 0 {:g} N I 21 N "VAL*"'.format(*label.position,
            label.font, label.font, label.thickness)
        return out + '\n'

    def string_to_text(self, string):
        return 'T2 {:g} {:g} {:g} {:g} 0 {:g} N V 21 N "{:s}"\n'.format(*string.position,
            string.font, string.font, string.thickness, string.value)

    def line_to_text(self, line):
        return 'DS {:g} {:g} {:g} {:g} {:g} 21\n'.format(*line.start, *line.end, line.thickness)

    def rect_to_text(self, rect):
        return ''.join([self.line_to_text(line) for line in rect.lines])

    def pad_to_text(self, pad):
        style = 'R' if pad.style == exporter.AbstractPad.STYLE_RECT else 'C'

        out = '$PAD\n'
        out += 'Sh "{:s}" {:s} {:g} {:g} 0 0 0\n'.format(str(pad.number), style, *pad.size)
        if pad.family == exporter.AbstractPad.FAMILY_SMD:
            out += 'Dr 0 0 0\n'
            out += 'At SMD N {:08X}\n'.format(pad.copper | pad.mask | pad.paste)
        else:
            out += 'Dr {:g} 0 0\n'.format(pad.diameter)
            if pad.copper == 0:
                out += 'At HOLE N {:08X}\n'.format(0xFFFF | pad.mask | pad.paste)
            else:
                out += 'At STD N {:08X}\n'.format(pad.copper | pad.mask | pad.paste)
        out += 'Ne 0 ""\n'
        out += 'Po {:g} {:g}\n'.format(*pad.position)
        out += '$EndPAD'
        return out + '\n'

    def poly_to_text(self, poly):
        out = 'DP 0 0 0 0 {:d} {:g} {:d}'.format(len(poly.vertices), poly.thickness, poly.layer)
        for vertex in poly.vertices:
            out += '\nDl {:g} {:g}'.format(*vertex)
        return out + '\n'

    def footprint_to_text(self, footprint):
        timestamp = time.time()

        out = '$MODULE {:s}\n'.format(footprint.name)
        out += 'Po 0 0 0 15 {:08X} 00000000 ~~\n'.format(int(timestamp))
        out += 'Li {:s}\n'.format(footprint.name)
        if footprint.description is not None:
            out += 'Cd {:s}\n'.format(footprint.description)
        out += 'Sc 0\n'
        out += 'AR\n'
        out += 'Op 0 0 0\n'
        out += 'At SMD\n'

        objects = footprint.generate()

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

        out += '$SHAPE3D\n'
        out += 'Na "{:s}/{:s}.{:s}"\n'.format(self.model_path, footprint.model, self.model_type)
        out += 'Sc 1 1 1\n'
        out += 'Of 0 0 0\n'
        out += 'Ro 0 0 0\n'
        out += '$EndSHAPE3D\n'
        out += '$EndMODULE {:s}\n'.format(footprint.name)

        return out

    def generate(self, part):
        return self.footprint_to_text(part)

    @staticmethod
    def extract_part_name(part):
        return re.sub(re.compile(r'^.*\$MODULE (CP.*?)\n.*$', re.M | re.S), r'\1', part)

    @staticmethod
    def archive(parts):
        timestring = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:{:s}')

        footprints = {}
        for part in parts:
            footprints.update({Converter.extract_part_name(part): part})
        names = list(footprints.keys())
        names.sort()

        out = 'PCBNEW-LibModule-V1 {:s}\n'.format(timestring)
        out += '# encoding utf-8\n'
        out += 'Units mm\n'
        out += '$INDEX\n'
        for name in names:
            out += name + '\n'
        out += '$EndINDEX\n'
        for name in names:
            out += footprints[name]
        out += '$EndLIBRARY\n'

        return out
