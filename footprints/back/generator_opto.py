#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import generator


class PlccFootprint(generator.Footprint):
    NUMBERING_REGULAR, NUMBERING_REVERSED = range(0, 2)

    def __init__(self, name, count, size, space, numberStyle, body, style, description):
        generator.Footprint.__init__(self, name=name, description=description)
        self.count = count
        self.size = size #Pad width, height
        self.space = space #Horizontal and vertical spaces between pads
        self.numberStyle = numberStyle
        self.body = body
        self.thickness = style[0]
        self.gap = style[2]

        self.dotRadius = self.thickness / 2.
        self.label = generator.Label(name=name, position=(0.0, 0.0), thickness=self.thickness, font=style[1])

        self.generate()

    def generate(self):
        count = self.count / 2
        offset = self.space[0] / 2. if count % 2 == 0 else 0.

        borders = (self.body[0] / 2., self.body[1] / 2.)
        minimalBorderX = (count / 2) * self.space[0] + self.size[0] / 2. - offset + self.thickness / 2. + self.gap
        if minimalBorderX > borders[0]:
            borders = (minimalBorderX, borders[1])

        if self.numberStyle == PlccFootprint.NUMBERING_REGULAR:
            for pin in range(0, count):
                index = pin - count / 2
                x = index * self.space[0] + offset

                self.pads.append(generator.SmdPad(1 + pin, self.size, (x, self.space[1])))
                self.pads.append(generator.SmdPad(self.count - pin, self.size, (x, -self.space[1])))
        elif self.numberStyle == PlccFootprint.NUMBERING_REVERSED:
            if self.count != 4:
                raise Exception()

            #Fixed pin numbers
            self.pads.append(generator.SmdPad(1, self.size, (-self.space[0] / 2., self.space[1])))
            self.pads.append(generator.SmdPad(2, self.size, (-self.space[0] / 2., -self.space[1])))
            self.pads.append(generator.SmdPad(3, self.size, (self.space[0] / 2., -self.space[1])))
            self.pads.append(generator.SmdPad(4, self.size, (self.space[0] / 2., self.space[1])))

        self.lines = []
        self.lines.append(generator.Line((borders[0], borders[1]), (-borders[0], borders[1]), self.thickness))
        self.lines.append(generator.Line((borders[0], -borders[1]), (-borders[0], -borders[1]), self.thickness))
        self.lines.append(generator.Line((borders[0], borders[1]), (borders[0], -borders[1]), self.thickness))
        self.lines.append(generator.Line((-borders[0], borders[1]), (-borders[0], -borders[1]), self.thickness))

        dotMarkOffset = (-((count / 2) * self.space[0] - offset), self.space[1] + self.size[1] / 2. + self.gap\
                + self.dotRadius + self.thickness / 2.)
        self.circles.append(generator.Circle(dotMarkOffset, self.dotRadius, self.thickness))

        processFunc = lambda x: generator.collide_line(x, self.pads, self.thickness, self.gap)
        processedLines = map(processFunc, self.lines)
        self.lines = []
        map(self.lines.extend, processedLines)


class Autogen:
    STYLE_THIN, STYLE_THICK = (0.16, 0.82, 0.18), (0.2, 1.0, 0.25)

    def __init__(self, modelType="wrl", isNew=False, path=None):
        self.parts = []

        if isNew:
            self.converter = generator.NewConverter("opto/", path, "opto", modelType)
        else:
            self.converter = generator.OldConverter("opto/")

        #Based on specifications from chinese LED
        self.parts.append(PlccFootprint(name="LED3528-PLCC4", count=4, size=(0.9, 1.3), space=(1.7, 1.4),
                numberStyle=PlccFootprint.NUMBERING_REVERSED, body=(2.8, 3.2), style=Autogen.STYLE_THIN,
                description=""))
        self.parts.append(PlccFootprint(name="LED3528-PLCC6", count=6, size=(0.6, 1.2), space=(0.95, 1.5),
                numberStyle=PlccFootprint.NUMBERING_REGULAR, body=(2.8, 3.2), style=Autogen.STYLE_THIN,
                description=""))
        self.parts.append(PlccFootprint(name="LED5050-PLCC6", count=6, size=(1.2, 2.1), space=(1.55, 2.1),
                numberStyle=PlccFootprint.NUMBERING_REGULAR, body=(5.0, 5.0), style=Autogen.STYLE_THICK,
                description=""))
        self.parts.append(PlccFootprint(name="LED6050-PLCC6", count=6, size=(1.5, 2.1), space=(2.1, 2.1),
                numberStyle=PlccFootprint.NUMBERING_REGULAR, body=(6.0, 5.0), style=Autogen.STYLE_THICK,
                description=""))

        self.parts.sort(key=lambda x: x.name)

    def text(self):
        return self.converter.generateDocument(self.parts)


parser = argparse.ArgumentParser()
parser.add_argument("-f", dest="format", help="output file format", default="wrl")
parser.add_argument("-o", dest="output", help="write footprints to specified directory", default=None)
parser.add_argument("-p", dest="pretty", help="use S-Expression format", default=False, action="store_true")
options = parser.parse_args()

ag = Autogen(options.format, options.pretty, options.output)
print ag.text()
