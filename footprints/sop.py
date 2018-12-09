#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class SOP(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=SOP.describe(descriptor), spec=spec)

        try:
            self.padSize = numpy.array(descriptor['pads']['regularPadSize'])
        except:
            self.padSize = numpy.array(descriptor['pads']['size'])

        try:
            self.sidePadSize = numpy.array(descriptor['pads']['sidePadSize'])
        except:
            self.sidePadSize = self.padSize

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.rows = int(descriptor['pins']['count'] / 2)
        self.margin = descriptor['pads']['margin']
        self.pitch = descriptor['pins']['pitch']
        self.sidePitch = self.pitch + (self.sidePadSize[0] - self.padSize[0]) / 2.0
        self.title = '{:s}-{:d}'.format(descriptor['package']['subtype'], descriptor['pins']['count'])

    def pad(self, position, count):
        return self.sidePadSize if position == 0 or position == count - 1 else self.padSize

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
        silkscreen.append(exporter.Label(self.title, (0.0, 0.0), self.thickness, self.font))

        # Horizontal offset to the first pin
        firstPinOffset = float(self.rows - 3) * self.pitch / 2.0 + self.sidePitch

        # Body outline
        outlineMargin = numpy.array([0.0, (self.margin - self.gap) * 2.0 - self.thickness, 0.0])
        outlineSize = numpy.minimum(self.bodySize, self.bodySize + outlineMargin)
        topCorner = outlineSize / 2.0
        silkscreen.append(exporter.Rect(topCorner, -topCorner, self.thickness))

        # Outer first pin mark
        dotMarkPosition = numpy.array([
                -(firstPinOffset + self.sidePadSize[0] / 2.0 + self.gap + self.thickness),
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
        for i in range(0, self.rows):
            x = self.spacing(i, self.rows) - firstPinOffset
            pads.append(exporter.SmdPad(i + 1, self.pad(i, self.rows), (x, y)))
            pads.append(exporter.SmdPad(i + 1 + self.rows, self.pad(i, self.rows), (-x, -y)))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor:
            return descriptor['description']
        else:
            round1f = lambda x: '{:d}'.format(int(x)) if int(x * 10) == int(x) * 10 else '{:.1f}'.format(x)
            round2f = lambda x: '{:.1f}'.format(x) if int(x * 100) == int(x * 10) * 10 else '{:.2f}'.format(x)
            widthStr = round1f(descriptor['body']['size'][0])
            pitchStr = round2f(descriptor['pins']['pitch'])
            return '{:d} leads, body width {:s} mm, pitch {:s} mm'.format(
                    descriptor['pins']['count'], widthStr, pitchStr)


types = [SOP]
