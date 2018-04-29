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
    def __init__(self, modelPath, libraryPath=None, libraryName=None, modelType='wrl'):
        if modelType != 'wrl' and modelType != 'x3d':
            raise Exception()
        self.pathToModels = modelPath
        self.modelType = modelType
        self.libraryPath = libraryPath if libraryName is not None else None
        self.libraryName = libraryName if libraryPath is not None else None

    def circleToText(self, circle):
        if circle.part is not None:
            # Arc
            angle = circle.part[0] * math.pi / 180.0
            start = (circle.position[0] + math.cos(angle) * circle.radius,
                    circle.position[1] + math.sin(angle) * circle.radius)
            return 'DA %.6f %.6f %.6f %.6f %i %.6f 21' % (circle.position[0], circle.position[1],
                    start[0], start[1], int(abs(circle.part[1] - circle.part[0]) * 10.0), circle.thickness)
        else:
            # Circle
            return 'DC %.6f %.6f %.6f %.6f %.6f 21' % (circle.position[0], circle.position[1],
                    circle.position[0], circle.position[1] + circle.radius, circle.thickness)

    def labelToText(self, label):
        if label is None:
            return ''

        out = ''
        out += 'T0 %.6f %.6f %.6f %.6f 0 %.6f N V 21 N "%s"\n' % (label.position[0], label.position[1],
                label.font, label.font, label.thickness, label.name)
        out += 'T1 %.6f %.6f %.6f %.6f 0 %.6f N I 21 N "VAL*"' % (label.position[0], label.position[1],
                label.font, label.font, label.thickness)
        return out

    def stringToText(self, string):
        return 'T2 %.6f %.6f %.6f %.6f 0 %.6f N V 21 N "%s"' % (string.position[0], string.position[1],
                string.font, string.font, string.thickness, string.value)

    def lineToText(self, line):
        return 'DS %.6f %.6f %.6f %.6f %.6f 21' % (line.start[0], line.start[1], line.end[0], line.end[1],
                line.thickness)

    def rectToText(self, rect):
        return ''.join([self.lineToText(line) for line in rect.lines])

    def padToText(self, pad):
        style = 'R' if pad.style == exporter.AbstractPad.STYLE_RECT else 'C'

        out = ''
        out += '$PAD\n'
        out += 'Sh "%s" %s %.6f %.6f 0 0 0\n' % (str(pad.number), style, pad.size[0], pad.size[1])
        if pad.family == exporter.AbstractPad.FAMILY_SMD:
            out += 'Dr 0 0 0\n'
            out += 'At SMD N %08X\n' % (pad.copper | pad.mask | pad.paste)
        else:
            out += 'Dr %.6f 0 0\n' % (pad.diameter)
            if pad.copper == 0:
                out += 'At HOLE N %08X\n' % (0xFFFF | pad.mask | pad.paste)
            else:
                out += 'At STD N %08X\n' % (pad.copper | pad.mask | pad.paste)
        out += 'Ne 0 ""\n'
        out += 'Po %.6f %.6f\n' % (pad.position[0], pad.position[1])
        out += '$EndPAD'
        return out

    def polyToText(self, poly):
        out = 'DP 0 0 0 0 %u %.6f %u' % (len(poly.vertices), poly.thickness, poly.layer)
        for vertex in poly.vertices:
            out += '\nDl %.6f %.6f' % (vertex[0], vertex[1])
        return out

    def footprintToText(self, footprint):
        timestamp = time.time()
        out = ''

        out += '$MODULE %s\n' % (footprint.name)
        out += 'Po 0 0 0 15 %08X 00000000 ~~\n' % (int(timestamp))
        out += 'Li %s\n' % (footprint.name)
        if footprint.description is not None:
            out += 'Cd %s\n' % (footprint.description)
        out += 'Sc 0\n'
        out += 'AR\n'
        out += 'Op 0 0 0\n'
        out += 'At SMD\n'

        objects = footprint.generate()

        for obj in filter(lambda x: isinstance(x, exporter.Label), objects):
            out += self.labelToText(obj) + '\n'
        for obj in filter(lambda x: isinstance(x, exporter.String), objects):
            out += self.stringToText(obj) + '\n'
        for obj in filter(lambda x: isinstance(x, exporter.Circle), objects):
            out += self.circleToText(obj) + '\n'
        for obj in filter(lambda x: isinstance(x, exporter.Line), objects):
            out += self.lineToText(obj) + '\n'
        for obj in filter(lambda x: isinstance(x, exporter.Rect), objects):
            out += self.rectToText(obj)
        for obj in filter(lambda x: isinstance(x, exporter.Poly), objects):
            out += self.polyToText(obj) + '\n'
        for obj in filter(lambda x: isinstance(x, exporter.AbstractPad), objects):
            out += self.padToText(obj) + '\n'

        out += '$SHAPE3D\n'
        out += 'Na "%s%s.%s"\n' % (self.pathToModels, footprint.model, self.modelType)
        out += 'Sc 1 1 1\n'
        out += 'Of 0 0 0\n'
        out += 'Ro 0 0 0\n'
        out += '$EndSHAPE3D\n'
        out += '$EndMODULE %s\n' % footprint.name

        return out

    def generate(self, part):
        return self.footprintToText(part)

    @staticmethod
    def extractPartName(part):
        return re.sub(re.compile(r'^.*\$MODULE (CP.*?)\n.*$', re.M | re.S), r'\1', part)

    @staticmethod
    def archive(parts):
        timestring = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')

        footprints = {}
        [footprints.update({Converter.extractPartName(part): part}) for part in parts]
        names = list(footprints.keys())
        names.sort()

        out = ''
        out += 'PCBNEW-LibModule-V1 %s\n' % (timestring)
        out += '# encoding utf-8\n'
        out += 'Units mm\n'
        out += '$INDEX\n'
        for name in names:
            out += name + '\n'
        out += '$EndINDEX\n'
        for name in names:
            out += footprints[name]
        out += '$EndLIBRARY'

        return out
