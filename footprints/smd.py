#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class Chip(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=Chip.describe(descriptor), spec=spec)

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.padSize = numpy.array(descriptor['pads']['size'])
        self.pitch = descriptor['pins']['pitch']
        self.mapping = descriptor['pins']['names'] if 'names' in descriptor['pins'] else ['1', '2']

        self.markArrow = descriptor['mark']['arrow'] if 'arrow' in descriptor['mark'] else False
        self.markBar = descriptor['mark']['bar'] if 'bar' in descriptor['mark'] else False
        self.markDot = descriptor['mark']['dot'] if 'dot' in descriptor['mark'] else False
        self.markVertical = descriptor['mark']['vertical'] if 'vertical' in descriptor['mark'] else False
        self.markWrap = descriptor['mark']['wrap'] if 'wrap' in descriptor['mark'] else False

        self.centeredArrow, self.filledArrow, self.verification = True, False, True

    def generate(self):
        return self.generateCompact()

    def generateCompact(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        center = (self.pitch + self.padSize[0]) / 2.0

        if self.markArrow or self.markWrap:
            # Horizontal border
            horiz = (self.pitch - self.thickness) / 2.0 - self.gap
            # Vertical border
            vert = (self.padSize[1] - self.thickness) / 2.0
        else:
            # Horizontal border
            horiz = self.bodySize[0] / 2.0
            # Vertical border
            minVert = (self.padSize[1] + self.thickness) / 2.0 + self.gap
            minLineVert = self.padSize[1] / 2.0 + self.thickness + self.gap
            if minVert < self.bodySize[1] / 2.0 < minLineVert:
                vert = minLineVert
            elif self.bodySize[1] / 2.0 < minVert:
                vert = minVert
            else:
                vert = self.bodySize[1] / 2.0

        pads = []
        pads.append(exporter.SmdPad(self.mapping[0], self.padSize, (-center, 0.0)))
        pads.append(exporter.SmdPad(self.mapping[1], self.padSize, (center, 0.0)))

        if not self.markArrow:
            if self.markVertical:
                objects.append(exporter.Line((0, vert), (0, -vert), self.thickness))
            else:
                objects.append(exporter.Line((horiz, vert), (-horiz, vert), self.thickness))
                objects.append(exporter.Line((horiz, -vert), (-horiz, -vert), self.thickness))

        if not self.markArrow and not self.markWrap:
            lines = []
            lines.append(exporter.Line((horiz, vert), (horiz, -vert), self.thickness))
            lines.append(exporter.Line((-horiz, vert), (-horiz, -vert), self.thickness))

            processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
            [objects.extend(processFunc(line)) for line in lines]

        if self.markDot and self.verification:
            dotMarkOffset = center + self.padSize[0] / 2.0 + self.gap + self.thickness
            objects.append(exporter.Circle((-dotMarkOffset, 0.0), self.thickness / 2.0, self.thickness))

        if self.markBar:
            horizPolar = horiz - self.thickness # Outer border without polarization
            points = [(-horiz, -vert), (-horiz, vert), (-horizPolar, vert), (-horizPolar, -vert)]
            objects.append(exporter.Line(points[0], points[1], self.thickness))
            objects.append(exporter.Line(points[2], points[3], self.thickness))
            objects.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        if self.markArrow:
            if self.centeredArrow:
                horizRight, horizLeft = 0.5 * vert, -0.5 * vert
            else:
                horizRight, horizLeft = horiz, horiz - vert

            objects.append(exporter.Line((-horizRight, vert), (-horizRight, -vert), self.thickness))
            points = [(-horizLeft, vert), (-horizLeft, -vert), (-horizRight, 0)]
            objects.append(exporter.Line(points[1], points[2], self.thickness))
            objects.append(exporter.Line(points[2], points[0], self.thickness))
            if self.filledArrow:
                objects.append(exporter.Line(points[0], points[1], self.thickness))
                objects.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        objects.extend(pads)
        return objects

    def generateLarge(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        if self.markWrap:
            # Scale outline to pad size
            outline = numpy.array([self.padSize[0] * 2.0 + self.pitch, self.padSize[1]])
            body = numpy.maximum(self.bodySize, outline)
        else:
            body = self.bodySize

        center = self.pitch / 2.0 + self.padSize[0] / 2.0
        offset = self.gap + self.thickness / 2.0

        horiz0 = self.pitch / 2.0 # Inner border
        horiz1 = body[0] / 2.0 + offset # Outer border without polarization
        horiz2 = horiz1 - self.thickness # Polarization line
        vert = body[1] / 2.0 + offset # Vertical border

        pads = []
        pads.append(exporter.SmdPad(self.mapping[0], self.padSize, (-center, 0)))
        pads.append(exporter.SmdPad(self.mapping[1], self.padSize, (center, 0)))
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)

        lines = []
        # Right lines
        lines.append(exporter.Line((horiz0, vert), (horiz1, vert), self.thickness))
        lines.append(exporter.Line((horiz0, -vert), (horiz1, -vert), self.thickness))
        lines.append(exporter.Line((horiz1, vert), (horiz1, -vert), self.thickness))

        # Left lines
        lines.append(exporter.Line((-horiz0, vert), (-horiz1, vert), self.thickness))
        lines.append(exporter.Line((-horiz0, -vert), (-horiz1, -vert), self.thickness))
        if self.markArrow or self.markBar or self.markDot:
            lines.append(exporter.Line((-horiz2, vert), (-horiz2, -vert), self.thickness))
        lines.append(exporter.Line((-horiz1, vert), (-horiz1, -vert), self.thickness))

        [objects.extend(processFunc(line)) for line in lines]

        objects.extend(pads)
        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None


class SOT(exporter.Footprint):
    class PadDesc:
        def __init__(self, number, position, side, pattern, descriptor=None):
            if descriptor is None and pattern is None:
                # Not enough information
                raise Exception()
            if number is None != position is None:
                raise Exception()

            if number is not None:
                self.number = number

            try:
                self.name = descriptor['name']
            except (KeyError, TypeError):
                if number is not None:
                    self.name = str(number)

            try:
                self.offset = numpy.array(descriptor['offset'])
            except (KeyError, TypeError):
                self.offset = pattern.offset if pattern is not None else numpy.zeros(2)

            try:
                self.size = numpy.array(descriptor['size'])
            except (KeyError, TypeError):
                self.size = pattern.size

            if position is not None:
                self.position = position + self.offset * [1, side]

        @classmethod
        def makePattern(cls, descriptor):
            if descriptor is None:
                raise Exception()

            return cls(None, None, None, None, descriptor)


    def __init__(self, spec, descriptor):
        super().__init__(self, name=descriptor['title'], description=SOT.describe(descriptor),
                model=SOT.model(descriptor), spec=spec)

        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.bodySize = numpy.array(descriptor['body']['size'])

        try:
            self.markDot = descriptor['mark']['dot']
        except:
            self.markDot = False
        try:
            self.markTri = descriptor['mark']['tri']
        except:
            self.markTri = False

        try:
            padPattern = SOT.PadDesc.makePattern(descriptor['pads']['default'])
        except KeyError:
            padPattern = None

        self.pads = []
        for i in range(1, self.count + 1):
            position = self.calcPadPosition(i - 1)
            side = self.calcPadSide(i - 1)

            key = str(i)
            if key not in descriptor['pins'] or descriptor['pins'][key] is not None:
                try:
                    self.pads.append(SOT.PadDesc(i, position, side, padPattern, descriptor['pads'][key]))
                except KeyError:
                    self.pads.append(SOT.PadDesc(i, position, side, padPattern))
            elif key in descriptor['pads']:
                # Pin deleted, pad is ignored
                raise Exception()

        # Vertical border
        lowerPads, upperPads = [], []
        for pad in self.pads:
            if pad.number <= int(self.count / 2):
                lowerPads.append(pad)
            else:
                upperPads.append(pad)

        lowerBound = min([pad.position[1] - pad.size[1] / 2.0 for pad in lowerPads])
        upperBound = max([pad.position[1] + pad.size[1] / 2.0 for pad in upperPads])
        lowerBound -= self.gap + self.thickness / 2.0
        upperBound += self.gap + self.thickness / 2.0
        lowerBound = min(self.bodySize[1] / 2.0, lowerBound)
        upperBound = max(-self.bodySize[1] / 2.0, upperBound)

        self.borderSize = numpy.array([self.bodySize[0], lowerBound - upperBound])
        self.borderCenter = numpy.array([0.0, lowerBound + upperBound])

    def calcPadPosition(self, number):
        columns = int(self.count / 2)
        position = numpy.array([
                self.pitch * (number % columns - (columns - 1) / 2.0),
                self.bodySize[1] / 2.0])
        return position * self.calcPadSide(number)

    def calcPadSide(self, number):
        return -1 if int(number / int(self.count / 2)) else 1

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Body outline
        silkscreen.append(exporter.Rect(self.borderSize / 2.0 + self.borderCenter,
                -self.borderSize / 2.0 + self.borderCenter, self.thickness))

        # Outer polarity mark
        if self.markDot:
            # Assume that it is at least one pin at lower side
            firstPad = self.pads[0]
            dotMarkOffset = firstPad.position[0] - (firstPad.size[0] / 2.0 + self.gap + self.thickness)
            silkscreen.append(exporter.Circle((dotMarkOffset, firstPad.position[1]),
                    self.thickness / 2.0, self.thickness))

        # Inner polarity mark
        if self.markTri:
            triMarkOffset = min(1.0, self.borderSize[1] / 2.0)
            topCorner = self.borderSize / 2.0 + self.borderCenter
            points = [
                    (-topCorner[0], topCorner[1] - triMarkOffset),
                    (-topCorner[0], topCorner[1]),
                    (-topCorner[0] + triMarkOffset, topCorner[1])]
            silkscreen.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        for entry in self.pads:
            pads.append(exporter.SmdPad(entry.name, entry.size, entry.position))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None

    @staticmethod
    def model(descriptor):
        return descriptor['body']['model'] if 'model' in descriptor['body'] else None


types = [Chip, SOT]
