#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# crystals.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class CrystalSMD(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=CrystalSMD.describe(descriptor), spec=spec)

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.padSize = numpy.array(descriptor['pads']['size'])
        self.pitch = numpy.array(descriptor['pins']['pitch'])
        self.mapping = descriptor['pins']['names']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        axisOffsets = self.pitch / 2.0

        if len(self.mapping) == 2:
            pads.append(exporter.SmdPad(self.mapping[0], self.padSize, (-axisOffsets[0], 0.0)))
            pads.append(exporter.SmdPad(self.mapping[1], self.padSize, (axisOffsets[0], 0.0)))
        elif len(self.mapping) == 4:
            pads.append(exporter.SmdPad(self.mapping[0], self.padSize, (-axisOffsets[0], axisOffsets[1])))
            pads.append(exporter.SmdPad(self.mapping[1], self.padSize, (axisOffsets[0], axisOffsets[1])))
            pads.append(exporter.SmdPad(self.mapping[2], self.padSize, (axisOffsets[0], -axisOffsets[1])))
            pads.append(exporter.SmdPad(self.mapping[3], self.padSize, (-axisOffsets[0], -axisOffsets[1])))
        else:
            # Unsupported pin configuration
            raise Exception()

        # First pin mark
        dotMarkPosition = numpy.array([
                -(axisOffsets[0] + self.padSize[0] / 2.0 + self.gap + self.thickness),
                axisOffsets[1]])
        silkscreen.append(exporter.Circle(dotMarkPosition, self.thickness / 2.0, self.thickness))

        # Body outline
        outline = exporter.Rect(self.bodySize / 2.0, -self.bodySize / 2.0, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor.keys():
            return descriptor['description']
        else:
            round1f = lambda x: '{:d}'.format(int(x)) if int(x * 10) == int(x) * 10 else '{:.1f}'.format(x)
            bodySize = [round1f(x) for x in descriptor['body']['size'][0:2]]
            return 'Quartz crystal SMD {:s}x{:s} mm'.format(*bodySize)


class CrystalTH(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=CrystalTH.describe(descriptor), spec=spec)

        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.innerDiameter = descriptor['pads']['drill']
        self.padSize = numpy.array([descriptor['pads']['diameter'], descriptor['pads']['diameter']])
        self.bodySize = numpy.array(descriptor['body']['size'])

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Horizontal offset of the first pin
        firstPinOffset = -float(self.count - 1) * self.pitch / 2.0
        for i in range(0, self.count):
            x = firstPinOffset + self.pitch * i
            objects.append(exporter.HolePad(i + 1, self.padSize, (x, 0.0), self.innerDiameter))

        # Body outline
        arcRadius = self.bodySize[1] / 2.0
        arcOffset = self.bodySize[0] / 2.0 - arcRadius
        objects.append(exporter.Circle((-arcOffset, 0.0), arcRadius, self.thickness, (90.0, -90.0)))
        objects.append(exporter.Circle((arcOffset, 0.0), arcRadius, self.thickness, (-90.0, 90.0)))
        objects.append(exporter.Line((-arcOffset, arcRadius), (arcOffset, arcRadius), self.thickness))
        objects.append(exporter.Line((-arcOffset, -arcRadius), (arcOffset, -arcRadius), self.thickness))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


types = [
        CrystalSMD,
        CrystalTH
]
