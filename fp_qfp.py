#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fp_qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class QuadFlatPackage(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"],
                description=QuadFlatPackage.describe(descriptor))

        self.body = (descriptor["body"]["width"], descriptor["body"]["length"])
        self.padSize = (descriptor["pads"]["width"], descriptor["pads"]["length"])
        self.sidePadWidth = descriptor["pads"]["sideWidth"]
        self.count = (descriptor["pins"]["columns"], descriptor["pins"]["rows"])
        self.margin = descriptor["pins"]["margin"]
        self.pitch = descriptor["pins"]["pitch"]
        self.sidePitch = self.pitch + (self.sidePadWidth - self.padSize[0]) / 2.

        self.thickness = spec["thickness"]
        self.gap = spec["gap"]
        self.dotRadius = self.thickness / 2.
        self.markOffset = 1.0

        self.objects.append(exporter.Label(name=descriptor["title"], position=(0.0, 0.0), thickness=self.thickness,
                font=spec["font"]))

        self.generate()

    def delta(self, position, count):
        res = 0.0
        if position >= 1:
            res += self.sidePitch
        if position > 0:
            res += self.pitch * (position - 1)
        if position == count - 1:
            res += self.sidePitch - self.pitch
        return res

    def generate(self):
        #Borders
        outlineMargin = (self.margin - self.gap - self.thickness / 2.) * 2.
        outline = (min(self.body[0], self.body[0] + outlineMargin), min(self.body[1], self.body[1] + outlineMargin))
        borders = (outline[0] / 2., outline[1] / 2.)

        self.objects.append(exporter.Line((borders[0], -borders[1]), (-borders[0], -borders[1]), self.thickness))
        self.objects.append(exporter.Line((borders[0], borders[1]), (borders[0], -borders[1]), self.thickness))
        self.objects.append(exporter.Line((borders[0], borders[1]), (-borders[0], borders[1]), self.thickness))
        self.objects.append(exporter.Line((-borders[0], borders[1]), (-borders[0], -borders[1]), self.thickness))

        offset = lambda count: self.pitch / 2. if count % 2 == 0 else self.pitch

        #Outer polarity mark
        dotMarkOffset = ((self.count[0] / 2 - 1) * self.pitch + (self.sidePitch - self.pitch)
                + offset(self.count[0]) + self.sidePadWidth / 2. + self.gap + self.dotRadius + self.thickness / 2.)
        self.objects.append(exporter.Circle((-dotMarkOffset, self.body[1] / 2. + self.padSize[1] / 2. + self.margin),
                self.dotRadius, self.thickness))

        #Inner polarity mark
        points = [(-borders[0], borders[1] - self.markOffset), (-borders[0], borders[1]),
                (-borders[0] + self.markOffset, borders[1])]
        self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))

        width = lambda count, i: self.sidePadWidth if i == 0 or i == count - 1 else self.padSize[0]

        pads = []
        for i in range(0, self.count[0]):
            x = -((self.count[0] / 2 - 1) * self.pitch + (self.sidePitch - self.pitch) + offset(self.count[0]))
            y = self.body[1] / 2. + self.margin + self.padSize[1] / 2.

            w = width(self.count[0], i)
            h = self.padSize[1]

            numbers = (i + 1, i + 1 + self.count[0] + self.count[1])
            pads.append(exporter.SmdPad(numbers[0], (w, h), ( x + self.delta(i, self.count[0]),  y)))
            pads.append(exporter.SmdPad(numbers[1], (w, h), (-x - self.delta(i, self.count[0]), -y)))
        for i in range(0, self.count[1]):
            y = -((self.count[1] / 2 - 1) * self.pitch + (self.sidePitch - self.pitch) + offset(self.count[1]))
            x = self.body[0] / 2. + self.margin + self.padSize[1] / 2.

            w = width(self.count[1], i)
            h = self.padSize[1]

            numbers = (i + 1 + self.count[0], i + 1 + 2 * self.count[0] + self.count[1])
            pads.append(exporter.SmdPad(numbers[0], (h, w), ( x, -y - self.delta(i, self.count[1]))))
            pads.append(exporter.SmdPad(numbers[1], (h, w), (-x,  y + self.delta(i, self.count[1]))))

        pads.sort(key=lambda x: x.number)
        self.objects.extend(pads)

    @staticmethod
    def describe(descriptor):
        if "description" in descriptor.keys():
            return descriptor["description"]
        else:
            return "%u leads, body %ux%ux%.1f mm, pitch %.1f mm" % (
                    (descriptor["pins"]["columns"] + descriptor["pins"]["rows"]) * 2,
                    descriptor["body"]["width"], descriptor["body"]["length"], descriptor["body"]["height"],
                    descriptor["pins"]["pitch"])


groups = [QuadFlatPackage]
