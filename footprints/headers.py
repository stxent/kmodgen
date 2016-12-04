#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class PinHeader(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"],
                description=PinHeader.describe(descriptor))

        self.count = (descriptor["pins"]["columns"], descriptor["pins"]["rows"])
        self.pitch = descriptor["pins"]["pitch"]
        self.padDrill = descriptor["pads"]["drill"]
        self.padSize = (descriptor["pads"]["diameter"], descriptor["pads"]["diameter"])

        self.font = spec["font"]
        self.gap = spec["gap"]
        self.thickness = spec["thickness"]

        self.body = (self.count[0] * self.pitch, self.count[1] * self.pitch)
        self.outline = self.calcOutline()

        xCenterOffset = self.pitch * float(self.count[0] / 2)
        if self.count[0] % 2 == 0:
            xCenterOffset -= self.pitch / 2.
        yCenterOffset = -self.pitch * float(self.count[1] - 1) / 2.
        self.center = (xCenterOffset, yCenterOffset)

    def calcOutline(self):
        staticOffset = self.gap * 2. + self.thickness - self.pitch
        minOffsets = (staticOffset + self.padSize[0] + self.body[0], staticOffset + self.padSize[1] + self.body[1])
        return (max(minOffsets[0], self.body[0]), max(minOffsets[1], self.body[1]))

    def generate(self):
        objects = []
        borders = (self.outline[0] / 2., self.outline[1] / 2.)

        objects.append(exporter.Label(name=self.name, position=self.center,
                thickness=self.thickness, font=self.font))

        objects.append(exporter.Line((-borders[0] + self.center[0], borders[1] + self.center[1]),
                (borders[0] + self.center[0], borders[1] + self.center[1]), self.thickness))
        objects.append(exporter.Line((-borders[0] + self.center[0], -borders[1] + self.center[1]),
                (borders[0] + self.center[0], -borders[1] + self.center[1]), self.thickness))
        objects.append(exporter.Line((borders[0] + self.center[0], borders[1] + self.center[1]),
                (borders[0] + self.center[0], -borders[1] + self.center[1]), self.thickness))
        objects.append(exporter.Line((-borders[0] + self.center[0], borders[1] + self.center[1]),
                (-borders[0] + self.center[0], -borders[1] + self.center[1]), self.thickness))

        pads = []
        for x in range(0, self.count[0]):
            for y in range(0, self.count[1]):
                offset = (x * self.pitch, -y * self.pitch)
                number = x * self.count[1] + y
                style = exporter.AbstractPad.STYLE_CIRCLE if number > 0 else exporter.AbstractPad.STYLE_RECT
                pads.append(exporter.HolePad(number + 1, self.padSize, offset, self.padDrill, style))
        objects.extend(pads)

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor["description"] if "description" in descriptor.keys() else None


class BoxHeader(PinHeader):
    def __init__(self, spec, descriptor):
        PinHeader.__init__(self, spec, descriptor)

        self.body = (descriptor["body"]["length"], descriptor["body"]["width"])
        self.outline = self.calcOutline()


types = [PinHeader, BoxHeader]
