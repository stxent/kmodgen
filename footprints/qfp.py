#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class QuadFlatPackage(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=QuadFlatPackage.describe(descriptor), spec=spec)

        if 'regularPadSize' in descriptor['pads'].keys():
            self.padSize = numpy.array(descriptor['pads']['regularPadSize'])
        else:
            self.padSize = numpy.array(descriptor['pads']['size'])

        if 'sidePadSize' in descriptor['pads'].keys():
            self.sidePadSize = numpy.array(descriptor['pads']['sidePadSize'])
        else:
            self.sidePadSize = self.padSize

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.count = numpy.array([descriptor['pins']['columns'], descriptor['pins']['rows']])
        self.margin = descriptor['pins']['margin']
        self.pitch = descriptor['pins']['pitch']
        self.sidePitch = self.pitch + (self.sidePadSize[0] - self.padSize[0]) / 2.0

    def pad(self, position, count, rev):
        x, y = self.sidePadSize if position == 0 or position == count - 1 else self.padSize
        return numpy.array([x, y]) if not rev else numpy.array([y, x])

    def spacing(self, position, count):
        res = 0.0
        if position > 0:
            res += self.pitch * (position - 1)
        if position >= 1:
            res += self.sidePitch
        if position == count - 1:
            res += self.sidePitch - self.pitch
        return res

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Horizontal and vertical offsets of first pins on each side
        firstPinOffset = (numpy.asfarray(self.count) - 3.0) * self.pitch / 2.0 + self.sidePitch

        # Body outline
        outlineMargin = (self.margin - self.gap) * 2.0 - self.thickness
        outlineSize = numpy.minimum(self.bodySize, self.bodySize + outlineMargin)
        topCorner = outlineSize / 2.0
        silkscreen.append(exporter.Rect(topCorner, -topCorner, self.thickness))

        # Outer first pin mark
        dotMarkPosition = numpy.array([
                -(firstPinOffset[0] + self.sidePadSize[0] / 2.0 + self.gap + self.thickness),
                (self.bodySize[1] + self.padSize[1]) / 2.0 + self.margin])
        silkscreen.append(exporter.Circle(dotMarkPosition, self.thickness / 2.0, self.thickness))

        # Inner first pin mark
        triMarkOffset = 1.0
        triMarkPoints = [
                (-topCorner[0], topCorner[1] - triMarkOffset),
                (-topCorner[0], topCorner[1]),
                (-topCorner[0] + triMarkOffset, topCorner[1])]
        silkscreen.append(exporter.Poly(triMarkPoints, self.thickness, exporter.Layer.SILK_FRONT))

        # Horizontal pads
        y = (self.bodySize[1] + self.padSize[1]) / 2.0 + self.margin
        pad = lambda x: self.pad(x, self.count[0], False)
        for i in range(0, self.count[0]):
            x = -firstPinOffset[0] + self.spacing(i, self.count[0])
            pads.append(exporter.SmdPad(1 + i, pad(i), (x, y)))
            pads.append(exporter.SmdPad(1 + i + self.count[0] + self.count[1], pad(i), (-x, -y)))

        # Vertical pads
        x = (self.bodySize[0] + self.padSize[1]) / 2.0 + self.margin
        pad = lambda x: self.pad(x, self.count[1], True)
        for j in range(0, self.count[1]):
            y = -firstPinOffset[1] + self.spacing(j, self.count[1])
            pads.append(exporter.SmdPad(1 + j + self.count[0], pad(j), (x, -y)))
            pads.append(exporter.SmdPad(1 + j + 2 * self.count[0] + self.count[1], pad(j), (-x, y)))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor.keys():
            return descriptor['description']
        else:
            pinCount = (descriptor['pins']['columns'] + descriptor['pins']['rows']) * 2
            round1f = lambda x: '{:d}'.format(int(x)) if int(x * 10) == int(x) * 10 else '{:.1f}'.format(x)
            round2f = lambda x: '{:.1f}'.format(x) if int(x * 100) == int(x * 10) * 10 else '{:.2f}'.format(x)
            sizeStr = [round1f(x) for x in descriptor['body']['size'][0:2]]
            heightStr = round2f(descriptor['body']['size'][2])
            pitchStr = round2f(descriptor['pins']['pitch'])
            return '{:d} leads, body {:s}x{:s}x{:s} mm, pitch {:s} mm'.format(
                    pinCount, sizeStr[0], sizeStr[1], heightStr, pitchStr)


types = [QuadFlatPackage]
