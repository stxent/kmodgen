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
import numpy as np

import exporter


class Converter:
    def __init__(self, model_path, library_path=None, library_name=None, model_type='wrl'):
        if model_type not in ('wrl', 'x3d'):
            raise KeyError()
        self.model_path = model_path
        self.model_type = model_type
        self.library_path = library_path if library_name is not None else None
        self.library_name = library_name if library_path is not None else None

    @staticmethod
    def circle_to_text(circle):
        if circle.part is not None:
            # Arc
            angle = np.deg2rad(circle.part[0])
            start = (circle.position[0] + math.cos(angle) * circle.radius,
                     circle.position[1] + math.sin(angle) * circle.radius)
            return f'DA {circle.position[0]:g} {circle.position[1]:g} {start[0]:g} {start[1]:g}' \
                   f' {int(abs(circle.part[1] - circle.part[0]) * 10.0)} {circle.thickness:g} 21\n'

        # Circle
        return f'DC {circle.position[0]:g} {circle.position[1]:g} {circle.position[0]:g}'\
               f' {(circle.position[1] + circle.radius):g} {circle.thickness:g} 21\n'

    @staticmethod
    def label_to_text(label):
        if label is None:
            return ''

        out = ''
        out += f'T0 {label.position[0]:g} {label.position[1]:g} {label.font:g} {label.font:g} 0' \
               f' {label.thickness:g} N V 21 N "{label.text}"\n'
        out += f'T1 {label.position[0]:g} {label.position[1]:g} {label.font:g} {label.font:g} 0' \
               f' {label.thickness:g} N I 21 N "VAL*"'
        return out + '\n'

    @staticmethod
    def string_to_text(string):
        return f'T2 {string.position[0]:g} {string.position[1]:g} {string.font:g}' \
               f' {string.font:g} 0 {string.thickness:g} N V 21 N "{string.text}"\n'

    @staticmethod
    def line_to_text(line):
        return f'DS {line.start[0]:g} {line.start[1]:g}' \
               f' {line.end[0]:g} {line.end[1]:g} {line.thickness:g} 21\n'

    @staticmethod
    def rect_to_text(rect):
        return ''.join([Converter.line_to_text(line) for line in rect.lines])

    @staticmethod
    def pad_to_text(pad):
        style = 'R' if pad.style == exporter.AbstractPad.STYLE_RECT else 'C'

        out = '$PAD\n'
        out += f'Sh "{pad.text}" {style} {pad.size[0]:g} {pad.size[1]:g} 0 0 0\n'
        if pad.family == exporter.AbstractPad.FAMILY_SMD:
            out += 'Dr 0 0 0\n'
            out += f'At SMD N {(pad.copper.mask | pad.mask.mask | pad.paste.mask):08X}\n'
        else:
            if pad.style == exporter.AbstractPad.STYLE_OVAL:
                out += f'Dr {pad.diameter[0]:g} 0 0 O {pad.diameter[0]:g} {pad.diameter[1]:g}\n'
            else:
                out += f'Dr {pad.diameter:g} 0 0\n'
            if pad.copper.mask == 0:
                out += f'At HOLE N {(0xFFFF | pad.mask.mask | pad.paste.mask):08X}\n'
            else:
                out += f'At STD N {(pad.copper.mask | pad.mask.mask | pad.paste.mask):08X}\n'
        out += 'Ne 0 ""\n'
        out += f'Po {pad.position[0]:g} {pad.position[1]:g}\n'
        out += '$EndPAD'
        return out + '\n'

    @staticmethod
    def poly_to_text(poly):
        out = f'DP 0 0 0 0 {len(poly.vertices)} {poly.thickness:g} {poly.layer.mask}'
        for vertex in poly.vertices:
            out += f'\nDl {vertex[0]:g} {vertex[1]:g}'
        return out + '\n'

    def footprint_to_text(self, footprint):
        timestamp = time.time()

        out = f'$MODULE {footprint.name}\n'
        out += f'Po 0 0 0 15 {int(timestamp):08X} 00000000 ~~\n'
        out += f'Li {footprint.name}\n'
        if footprint.description is not None:
            out += f'Cd {footprint.description}\n'
        out += 'Sc 0\n'
        out += 'AR\n'
        out += 'Op 0 0 0\n'
        out += 'At SMD\n'

        objects = footprint.generate()

        for obj in filter(lambda x: isinstance(x, exporter.Label), objects):
            out += Converter.label_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.String), objects):
            out += Converter.string_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Circle), objects):
            out += Converter.circle_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Line), objects):
            out += Converter.line_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Rect), objects):
            out += Converter.rect_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Poly), objects):
            out += Converter.poly_to_text(obj)
        for obj in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            out += Converter.pad_to_text(obj)

        out += '$SHAPE3D\n'
        out += f'Na "{self.model_path}/{footprint.model}.{self.model_type}"\n'
        out += 'Sc 1 1 1\n'
        out += 'Of 0 0 0\n'
        out += 'Ro 0 0 0\n'
        out += '$EndSHAPE3D\n'
        out += f'$EndMODULE {footprint.name}\n'

        return out

    def generate(self, part):
        return self.footprint_to_text(part)

    @staticmethod
    def extract_part_name(part):
        return re.sub(re.compile(r'^.*\$MODULE (CP.*?)\n.*$', re.M | re.S), r'\1', part)

    @staticmethod
    def archive(parts):
        timestring = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')

        footprints = {}
        for part in parts:
            footprints.update({Converter.extract_part_name(part): part})
        names = list(footprints.keys())
        names.sort()

        out = f'PCBNEW-LibModule-V1 {timestring}\n'
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
