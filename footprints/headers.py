#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class PinHeader(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=PinHeader.describe(descriptor), spec=spec)

        self.count = numpy.array([descriptor['pins']['columns'], descriptor['pins']['rows']])
        self.pitch = descriptor['pins']['pitch']
        self.bodySize = numpy.asfarray(self.count) * self.pitch
        self.bodyCenter = numpy.asfarray(self.count - 1) * [1, -1] * (self.pitch / 2.0)
        self.padSize = numpy.array([descriptor['pads']['diameter'], descriptor['pads']['diameter']])
        self.padDrill = descriptor['pads']['drill']

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, self.bodyCenter, self.thickness, self.font))

        # Body outline
        outlineMargin = 2.0 * self.gap + self.thickness - self.pitch
        outlineSize = numpy.maximum(self.bodySize, self.bodySize + self.padSize + outlineMargin)
        objects.append(exporter.Rect(outlineSize / 2.0 + self.bodyCenter, -outlineSize / 2.0 + self.bodyCenter,
                self.thickness))

        # Pads
        for x in range(0, self.count[0]):
            for y in range(0, self.count[1]):
                offset = numpy.array([float(x), -float(y)]) * self.pitch
                number = 1 + x * self.count[1] + y
                style = exporter.AbstractPad.STYLE_CIRCLE if number > 1 else exporter.AbstractPad.STYLE_RECT
                objects.append(exporter.HolePad(number, self.padSize, offset, self.padDrill, style))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None


class RightAnglePinHeader(PinHeader):
    def __init__(self, spec, descriptor):
        PinHeader.__init__(self, spec, descriptor)

        projectionLength = descriptor['pins']['length'] - 0.5 * self.pitch
        self.bodySize += numpy.array([0.0, projectionLength])
        self.bodyCenter += numpy.array([0.0, projectionLength / 2.0])

    def generate(self):
        objects = PinHeader.generate(self)

        outlineMargin = 2.0 * self.gap + self.thickness - self.pitch
        outlineSize = numpy.maximum(self.bodySize, self.bodySize + self.padSize + outlineMargin)
        lineOffsets = (outlineSize[0] / 2.0, self.gap + (self.padSize[1] + self.thickness) / 2.0)
        objects.append(exporter.Line((lineOffsets[0] + self.bodyCenter[0], lineOffsets[1]),
                (-lineOffsets[0] + self.bodyCenter[0], lineOffsets[1]), self.thickness))
        return objects


class BoxHeader(PinHeader):
    def __init__(self, spec, descriptor):
        PinHeader.__init__(self, spec, descriptor)
        self.bodySize = numpy.array(descriptor['body']['size'])


class Jumper(PinHeader):
    def __init__(self, spec, descriptor):
        PinHeader.__init__(self, spec, descriptor)


types = [PinHeader, RightAnglePinHeader, BoxHeader, Jumper]
