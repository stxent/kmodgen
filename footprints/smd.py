#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class Chip(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"], description=Chip.describe(descriptor))

        self.size = (descriptor["pads"]["width"], descriptor["pads"]["height"])
        self.spacing = descriptor["pins"]["spacing"]
        self.body = (descriptor["body"]["width"], descriptor["body"]["height"])
        self.pinNames = descriptor["pins"]["names"] if "names" in descriptor["pins"].keys() else ["1", "2"]

        self.markArrow = descriptor["mark"]["arrow"] if "arrow" in descriptor["mark"].keys() else False
        self.markBar = descriptor["mark"]["bar"] if "bar" in descriptor["mark"].keys() else False
        self.markDot = descriptor["mark"]["dot"] if "dot" in descriptor["mark"].keys() else False
        self.markVertical = descriptor["mark"]["vertical"] if "vertical" in descriptor["mark"].keys() else False
        self.markWrap = descriptor["mark"]["wrap"] if "wrap" in descriptor["mark"].keys() else False

        self.thickness = spec["thickness"]
        self.gap = spec["gap"]

        self.dotRadius = self.thickness / 2.
        self.objects.append(exporter.Label(name=descriptor["title"], position=(0.0, 0.0), thickness=self.thickness,
                font=spec["font"]))
        self.centeredArrow, self.filledArrow, self.verification = True, False, True

        self.generateCompact()
#         self.generateLarge()

    def generateCompact(self):
        center = self.spacing / 2. + self.size[0] / 2.

        if self.markArrow or self.markWrap:
            #Horizontal border
            horiz = self.spacing / 2. - self.thickness / 2. - self.gap
            #Vertical border
            vert = self.size[1] / 2. - self.thickness / 2.
        else:
            #Horizontal border
            horiz = self.body[0] / 2.
            #Vertical border
            minVert = self.size[1] / 2. + self.gap + self.thickness / 2.
            minLineVert = self.size[1] / 2. + self.gap + self.thickness
            if minVert < self.body[1] / 2. < minLineVert:
                vert = minLineVert
            elif self.body[1] / 2. < minVert:
                vert = minVert
            else:
                vert = self.body[1] / 2.

        pads = []
        pads.append(exporter.SmdPad(self.pinNames[0], self.size, (-center, 0)))
        pads.append(exporter.SmdPad(self.pinNames[1], self.size, (center, 0)))
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)

        if not self.markArrow:
            if self.markVertical:
                self.objects.append(exporter.Line((0, vert), (0, -vert), self.thickness))
            else:
                self.objects.append(exporter.Line((horiz, vert), (-horiz, vert), self.thickness))
                self.objects.append(exporter.Line((horiz, -vert), (-horiz, -vert), self.thickness))

        if not self.markArrow and not self.markWrap:
            lines = []
            lines.append(exporter.Line((horiz, vert), (horiz, -vert), self.thickness))
            lines.append(exporter.Line((-horiz, vert), (-horiz, -vert), self.thickness))
            processedLines = map(processFunc, lines)
            map(self.objects.extend, processedLines)

        if self.markDot and self.verification:
            dotMarkOffset = center + self.size[0] / 2. + self.gap + self.dotRadius + self.thickness / 2.
            self.objects.append(exporter.Circle((-dotMarkOffset, 0.0), self.dotRadius, self.thickness))
        if self.markBar:
            horizPolar = horiz - self.thickness #Outer border without polarization
            points = [(-horiz, -vert), (-horiz, vert), (-horizPolar, vert), (-horizPolar, -vert)]
            self.objects.append(exporter.Line(points[0], points[1], self.thickness))
            self.objects.append(exporter.Line(points[2], points[3], self.thickness))
            self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))
        if self.markArrow:
            if self.centeredArrow:
                horizRight, horizLeft = 0.5 * vert, -0.5 * vert
            else:
                horizRight, horizLeft = horiz, horiz - vert

            self.objects.append(exporter.Line((-horizRight, vert), (-horizRight, -vert), self.thickness))
            points = [(-horizLeft, vert), (-horizLeft, -vert), (-horizRight, 0)]
            self.objects.append(exporter.Line(points[1], points[2], self.thickness))
            self.objects.append(exporter.Line(points[2], points[0], self.thickness))
            if self.filledArrow:
                self.objects.append(exporter.Line(points[0], points[1], self.thickness))
                self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))

        self.objects.extend(pads)

    def generateLarge(self):
        if self.markWrap:
            #Scale outline to pad size
            outline = (self.size[0] * 2. + self.spacing, self.size[1])
            self.body = (max(self.body[0], outline[0]), max(self.body[1], outline[1]))

        center = self.spacing / 2. + self.size[0] / 2.
        offset = self.gap + self.thickness / 2.

        horiz0 = self.spacing / 2. #Inner border
        horiz1 = self.body[0] / 2. + offset #Outer border without polarization
        horiz2 = horiz1 - self.thickness #Plarization line
        vert = self.body[1] / 2. + offset #Vertical border

        pads = []
        pads.append(exporter.SmdPad(self.pinNames[0], self.size, (-center, 0)))
        pads.append(exporter.SmdPad(self.pinNames[1], self.size, (center, 0)))
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)

        lines = []
        #Right lines
        lines.append(exporter.Line((horiz0, vert), (horiz1, vert), self.thickness))
        lines.append(exporter.Line((horiz0, -vert), (horiz1, -vert), self.thickness))
        lines.append(exporter.Line((horiz1, vert), (horiz1, -vert), self.thickness))

        #Left lines
        lines.append(exporter.Line((-horiz0, vert), (-horiz1, vert), self.thickness))
        lines.append(exporter.Line((-horiz0, -vert), (-horiz1, -vert), self.thickness))
        if self.markArrow or self.markBar or self.markDot:
            lines.append(exporter.Line((-horiz2, vert), (-horiz2, -vert), self.thickness))
        lines.append(exporter.Line((-horiz1, vert), (-horiz1, -vert), self.thickness))

        processedLines = map(processFunc, lines)
        map(self.objects.extend, processedLines)

        self.objects.extend(pads)
        
    @staticmethod
    def describe(descriptor):
        return descriptor["description"] if "description" in descriptor.keys() else ""


class SmallOutlineTransistor23(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"], description=Chip.describe(descriptor),
                model=descriptor["body"]["model"] if "model" in descriptor["body"].keys() else None)

        self.size = (descriptor["pads"]["width"], descriptor["pads"]["height"])
        
        if "centralPadWidth" in descriptor["pads"].keys():
            self.centralPadSize = (descriptor["pads"]["centralPadWidth"], self.size[0])
        else:
            self.centralPadSize = self.size
        
        self.spacing = (descriptor["pins"]["horizontalSpacing"], descriptor["pins"]["verticalSpacing"])
        self.thickness = spec["thickness"]
        self.gap = spec["gap"]
        self.pinNames = descriptor["pins"]["names"]
        self.markDot = descriptor["mark"]["dot"] if "dot" in descriptor["mark"].keys() else False
        self.markTri = descriptor["mark"]["tri"] if "tri" in descriptor["mark"].keys() else False

        self.dotRadius = self.thickness / 2.
        self.objects.append(exporter.Label(name=descriptor["title"], position=(0.0, 0.0), thickness=self.thickness,
                font=spec["font"]))

        #Vertical border
        border = (self.spacing[1] - self.size[1]) / 2. - self.gap - self.thickness / 2.
        self.body = (descriptor["body"]["width"], border * 2.)
        self.markOffset = border

        self.generate()

    def generate(self):
        yOffset = self.spacing[1] / 2.
        outline = (self.body[0] / 2., self.body[1] / 2.)

        #Outline
        self.objects.append(exporter.Line((outline[0], -outline[1]), (-outline[0], -outline[1]), self.thickness))
        self.objects.append(exporter.Line((outline[0], outline[1]), (outline[0], -outline[1]), self.thickness))
        self.objects.append(exporter.Line((outline[0], outline[1]), (-outline[0], outline[1]), self.thickness))
        self.objects.append(exporter.Line((-outline[0], outline[1]), (-outline[0], -outline[1]), self.thickness))

        #First pin mark
        if self.markDot:
            #Outer polarity mark
            dotMarkOffset = self.spacing[0] + self.size[0] / 2. + self.gap + self.dotRadius + self.thickness / 2.
            self.objects.append(exporter.Circle((-dotMarkOffset, yOffset), self.dotRadius, self.thickness))
        if self.markTri:
            #Inner polarity mark
            points = [(-outline[0], outline[1] - self.markOffset), (-outline[0], outline[1]),
                    (-outline[0] + self.markOffset, outline[1])]
            self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))

        pads = []
        for i in range(0, 3):
            width = self.size[0] if i != 1 else self.centralPadSize[0]
            xOffset = self.spacing[0] * (i - 1)
            #Bottom row
            if self.pinNames[i] != "":
                pads.append(exporter.SmdPad(self.pinNames[i], (width, self.size[1]), (xOffset, yOffset)))
            #Top row
            if self.pinNames[i + 3] != "":
                pads.append(exporter.SmdPad(self.pinNames[i + 3], (width, self.size[1]), (-xOffset, -yOffset)))

        pads.sort(key=lambda x: x.number)
        self.objects.extend(pads)


class SmallOutlineTransistor223(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor["title"], description=Chip.describe(descriptor),
                model=descriptor["body"]["model"] if "model" in descriptor["body"].keys() else None)

        self.size = (descriptor["pads"]["width"], descriptor["pads"]["height"])
        self.powerPadSize = (descriptor["pads"]["powerPadWidth"], descriptor["pads"]["powerPadHeight"])
        self.spacing = (descriptor["pins"]["horizontalSpacing"], descriptor["pins"]["verticalSpacing"])
        self.body = (descriptor["body"]["width"], descriptor["body"]["height"])
        self.thickness = spec["thickness"]
        self.gap = spec["gap"]
        self.pinNames = descriptor["pins"]["names"]
        self.markDot = descriptor["mark"]["dot"] if "dot" in descriptor["mark"].keys() else False
        self.markTri = descriptor["mark"]["tri"] if "tri" in descriptor["mark"].keys() else False

        self.dotRadius = self.thickness / 2.
        self.markOffset = 1.0
        self.objects.append(exporter.Label(name=descriptor["title"], position=(0.0, 0.0), thickness=self.thickness,
                font=spec["font"]))

        self.generate()

    def generate(self):
        yOffset = self.spacing[1] / 2.
        outline = (self.body[0] / 2., self.body[1] / 2.)

        #Outline
        self.objects.append(exporter.Line((outline[0], -outline[1]), (-outline[0], -outline[1]), self.thickness))
        self.objects.append(exporter.Line((outline[0], outline[1]), (outline[0], -outline[1]), self.thickness))
        self.objects.append(exporter.Line((outline[0], outline[1]), (-outline[0], outline[1]), self.thickness))
        self.objects.append(exporter.Line((-outline[0], outline[1]), (-outline[0], -outline[1]), self.thickness))

        #First pin marks
        if self.markDot:
            #Outer polarity mark
            dotMarkOffset = self.spacing[0] + self.size[0] / 2. + self.gap + self.dotRadius + self.thickness / 2.
            self.objects.append(exporter.Circle((-dotMarkOffset, yOffset), self.dotRadius, self.thickness))
        if self.markTri:
            #Inner polarity mark
            points = [(-outline[0], outline[1] - self.markOffset), (-outline[0], outline[1]),
                    (-outline[0] + self.markOffset, outline[1])]
            self.objects.append(exporter.Poly(points, self.thickness, exporter.AbstractPad.Layer.SILK_FRONT))

        for i in range(0, 3):
            self.objects.append(exporter.SmdPad(self.pinNames[i], self.size, (self.spacing[0] * (i - 1), yOffset)))
        self.objects.append(exporter.SmdPad(self.pinNames[3], self.powerPadSize, (0.0, -yOffset)))

    @staticmethod
    def describe(descriptor):
        return descriptor["description"] if "description" in descriptor.keys() else ""


types = [Chip, SmallOutlineTransistor23, SmallOutlineTransistor223]
