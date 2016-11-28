#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fp_sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class SmallOutlinePackage(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"],
                description=SmallOutlinePackage.describe(descriptor))

        self.body = (descriptor["body"]["length"], descriptor["body"]["width"])
        self.padSize = (descriptor["pads"]["width"], descriptor["pads"]["length"])
        self.sidePadWidth = descriptor["pads"]["sideWidth"]
        self.count = descriptor["pins"]["count"]
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
        outline = (self.body[0], min(self.body[1], self.body[1] + outlineMargin))
        borders = (outline[0] / 2., outline[1] / 2.)

        count = self.count / 2
        offset = self.pitch / 2. if count % 2 == 0 else self.pitch

        self.objects.append(exporter.Line((borders[0], -borders[1]), (-borders[0], -borders[1]), self.thickness))
        self.objects.append(exporter.Line((borders[0], borders[1]), (borders[0], -borders[1]), self.thickness))
        self.objects.append(exporter.Line((borders[0], borders[1]), (-borders[0], borders[1]), self.thickness))
        self.objects.append(exporter.Line((-borders[0], borders[1]), (-borders[0], -borders[1]), self.thickness))

        #Outer polarity mark
        dotMarkOffset = ((count / 2 - 1) * self.pitch + (self.sidePitch - self.pitch) + offset
                + self.sidePadWidth / 2. + self.gap + self.dotRadius + self.thickness / 2.)
        self.objects.append(exporter.Circle((-dotMarkOffset, self.body[1] / 2. + self.margin + self.padSize[1] / 2.),
                self.dotRadius, self.thickness))

        #Inner polarity mark
        points = [(-borders[0], borders[1] - self.markOffset), (-borders[0], borders[1]),
                (-borders[0] + self.markOffset, borders[1])]
        self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))

        pads = []
        for i in range(0, count):
            x = -((count / 2 - 1) * self.pitch + (self.sidePitch - self.pitch) + offset)
            y = self.body[1] / 2. + self.margin + self.padSize[1] / 2.

            w = self.sidePadWidth if i == 0 or i == count - 1 else self.padSize[0]
            h = self.padSize[1]

            pads.append(exporter.SmdPad(i + 1 + count, (w, h), (-x - self.delta(i, count), -y)))
            pads.append(exporter.SmdPad(i + 1,         (w, h), ( x + self.delta(i, count),  y)))

        pads.sort(key=lambda x: x.number)
        self.objects.extend(pads)

    @staticmethod
    def describe(descriptor):
        if "description" in descriptor.keys():
            return descriptor["description"]
        else:
            return "%u leads, body width %.1f mm, pitch %.2f mm" % (
                    descriptor["pins"]["count"], descriptor["body"]["width"], descriptor["pins"]["pitch"])


groups = [SmallOutlinePackage]
