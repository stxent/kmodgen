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
        exporter.Footprint.__init__(self, name=descriptor['title'], description=Chip.describe(descriptor), spec=spec)

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


class SOT23(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'], description=SOT23.describe(descriptor),
                model=SOT23.model(descriptor), spec=spec)

        if 'regularPadSize' in descriptor['pads'].keys():
            self.padSize = numpy.array(descriptor['pads']['regularPadSize'])
        else:
            self.padSize = numpy.array(descriptor['pads']['size'])

        if 'centralPadSize' in descriptor['pads'].keys():
            self.centralPadSize = numpy.array(descriptor['pads']['centralPadSize'])
        else:
            self.centralPadSize = self.padSize

        self.pitch = numpy.array(descriptor['pins']['pitch'])
        self.mapping = descriptor['pins']['names']
        self.markDot = descriptor['mark']['dot'] if 'dot' in descriptor['mark'].keys() else False
        self.markTri = descriptor['mark']['tri'] if 'tri' in descriptor['mark'].keys() else False

        # Vertical border
        verticalPadMargin = (self.pitch[1] - self.padSize[1]) / 2.0 - self.gap - self.thickness / 2.0
        self.bodySize = numpy.array([descriptor['body']['size'][0], verticalPadMargin * 2.0])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        yOffset = self.pitch[1] / 2.0

        # Body outline
        topCorner = self.bodySize / 2.0
        silkscreen.append(exporter.Rect(topCorner, -topCorner, self.thickness))

        # Outer polarity mark
        if self.markDot:
            dotMarkOffset = self.pitch[0] + self.padSize[0] / 2.0 + self.gap + self.thickness
            silkscreen.append(exporter.Circle((-dotMarkOffset, yOffset), self.thickness / 2.0, self.thickness))

        # Inner polarity mark
        if self.markTri:
            points = [
                    (-topCorner[0], 0.0),
                    (-topCorner[0], topCorner[1]),
                    (-topCorner[0] + topCorner[1], topCorner[1])]
            silkscreen.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        for i in range(0, 3):
            pad = self.padSize if i != 1 else self.centralPadSize
            xOffset = self.pitch[0] * (i - 1)
            # Bottom row
            if self.mapping[i] != '':
                pads.append(exporter.SmdPad(self.mapping[i], pad, (xOffset, yOffset)))
            # Top row
            if self.mapping[i + 3] != '':
                pads.append(exporter.SmdPad(self.mapping[i + 3], pad, (-xOffset, -yOffset)))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else None

    @staticmethod
    def model(descriptor):
        return descriptor['body']['model'] if 'model' in descriptor['body'].keys() else None


class SOT223(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'], description=SOT223.describe(descriptor),
                model=SOT223.model(descriptor), spec=spec)

        self.bodySize = numpy.array(descriptor['body']['size'])
        self.padSize = numpy.array(descriptor['pads']['regularPadSize'])
        self.powerPadSize = numpy.array(descriptor['pads']['powerPadSize'])
        self.pitch = numpy.array(descriptor['pins']['pitch'])

        self.mapping = descriptor['pins']['names']
        self.markDot = descriptor['mark']['dot'] if 'dot' in descriptor['mark'].keys() else False
        self.markTri = descriptor['mark']['tri'] if 'tri' in descriptor['mark'].keys() else False

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        yOffset = self.pitch[1] / 2.0

        # Body outline
        topCorner = self.bodySize / 2.0
        objects.append(exporter.Rect(topCorner, -topCorner, self.thickness))

        # Outer polarity mark
        if self.markDot:
            dotMarkOffset = self.pitch[0] + self.padSize[0] / 2.0 + self.gap + self.thickness
            objects.append(exporter.Circle((-dotMarkOffset, yOffset), self.thickness / 2.0, self.thickness))

        # Inner polarity mark
        if self.markTri:
            triMarkOffset = 1.0
            triMarkPoints = [
                    (-topCorner[0], topCorner[1] - triMarkOffset),
                    (-topCorner[0], topCorner[1]),
                    (-topCorner[0] + triMarkOffset, topCorner[1])]
            objects.append(exporter.Poly(triMarkPoints, self.thickness, exporter.Layer.SILK_FRONT))

        for i in range(0, 3):
            objects.append(exporter.SmdPad(self.mapping[i], self.padSize, (self.pitch[0] * (i - 1), yOffset)))
        objects.append(exporter.SmdPad(self.mapping[3], self.powerPadSize, (0.0, -yOffset)))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else None

    @staticmethod
    def model(descriptor):
        return descriptor['body']['model'] if 'model' in descriptor['body'].keys() else None


types = [Chip, SOT23, SOT223]
