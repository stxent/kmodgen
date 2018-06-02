#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# switches.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class Button(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'], description=Button.describe(descriptor), spec=spec)

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.padSize = numpy.array(descriptor['pads']['size'])
        self.pitch = numpy.array(descriptor['pins']['pitch'])
        self.shielding = descriptor['pins']['shielding']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        pads.append(exporter.SmdPad(1, self.padSize, self.pitch / 2.0 * numpy.array([-1.0, +1.0])))
        pads.append(exporter.SmdPad(2, self.padSize, self.pitch / 2.0 * numpy.array([+1.0, +1.0])))
        pads.append(exporter.SmdPad(3, self.padSize, self.pitch / 2.0 * numpy.array([+1.0, -1.0])))
        pads.append(exporter.SmdPad(4, self.padSize, self.pitch / 2.0 * numpy.array([-1.0, -1.0])))

        if self.shielding:
            pads.append(exporter.SmdPad(5, self.padSize, self.pitch / 2.0 * numpy.array([1.0, 0.0])))

        # Body outline
        boundingBox = numpy.array([0.0, self.pitch[1] + self.padSize[1] + self.gap * 2.0 + self.thickness])
        outlineSize = numpy.maximum(self.bodySize, boundingBox)
        outline = exporter.Rect(outlineSize / 2.0, -outlineSize / 2.0, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        # Central circle
        silkscreen.append(exporter.Circle((0.0, 0.0), min(self.bodySize) / 4.0, self.thickness))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


types = [
        Button
]
