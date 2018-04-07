#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# conncetors.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class FlexibleFlatCableConnector(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=FlexibleFlatCableConnector.describe(descriptor))

        self.mountPadSize = (descriptor['pads']['mountWidth'], descriptor['pads']['mountHeight'])
        self.mountPadSpacing = (descriptor['mount']['horizontalSpacing'], descriptor['mount']['verticalSpacing'])
        self.signalPadSize = (descriptor['pads']['width'], descriptor['pads']['height'])
        self.signalPadOffset = descriptor['pads']['offset']
        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.bodyHeight = descriptor['body']['height']
        self.bodyWidthIncrease = descriptor['body']['widthIncrease']

        self.font = spec['font']
        self.gap = spec['gap']
        self.thickness = spec['thickness']

    def generate(self):
        objects = []
        objects.append(exporter.Label(name=self.name, position=(0.0, 0.0), thickness=self.thickness, font=self.font))

        totalPadsWidth = self.pitch * (self.count - 1)
        borders = ((self.bodyWidthIncrease * 2.0 + totalPadsWidth) / 2.0, self.bodyHeight / 2.0)
        mountPadOffset = (self.mountPadSpacing[0] + totalPadsWidth / 2.0,
                self.signalPadOffset - self.mountPadSpacing[1])

        dotMarkRadius = self.thickness / 2.0
        dotMarkOffset = (-totalPadsWidth / 2.0, -(self.signalPadOffset + self.signalPadSize[1] / 2.0
                + self.gap + self.thickness))

        objects.append(exporter.Circle(dotMarkOffset, dotMarkRadius, self.thickness))

        pads = []

        # Mounting pads
        pads.append(exporter.SmdPad('', self.mountPadSize, (mountPadOffset[0], -mountPadOffset[1])))
        pads.append(exporter.SmdPad('', self.mountPadSize, (-mountPadOffset[0], -mountPadOffset[1])))

        # Signal pads
        for i in range(0, self.count):
            x = -totalPadsWidth / 2.0 + i * self.pitch
            pads.append(exporter.SmdPad(i + 1, self.signalPadSize, (x, -self.signalPadOffset)))

        objects += pads

        lines = []
        lines.append(exporter.Line((borders[0], borders[1]), (-borders[0], borders[1]), self.thickness))
        lines.append(exporter.Line((borders[0], -borders[1]), (-borders[0], -borders[1]), self.thickness))
        lines.append(exporter.Line((borders[0], borders[1]), (borders[0], -borders[1]), self.thickness))
        lines.append(exporter.Line((-borders[0], borders[1]), (-borders[0], -borders[1]), self.thickness))

        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [objects.extend(processFunc(line)) for line in lines]

        return objects

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor.keys():
            return descriptor['description']
        else:
            pitch = descriptor['pins']['pitch']
            pitchStr = '%.1f' % pitch if int(pitch * 100) == int(pitch * 10) * 10 else '%.2f' % pitch
            return 'FFC/FPC connector, %s mm pitch, surface mount, %s contact style, %u circuits'\
                    % (pitchStr, descriptor['pins']['style'], descriptor['pins']['count'])


class IpxFootprint(exporter.Footprint):
    def __init__(self, spec, descriptor, coreSize, coreOffset, sideSize, sideOffset):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description='Miniature RF connector for high-frequency signals')

        self.coreOffset, self.coreSize = coreOffset, coreSize
        self.sideOffset, self.sideSize = sideOffset, sideSize

        self.font = spec['font']
        self.gap = spec['gap']
        self.thickness = spec['thickness']

        self.body = (descriptor['body']['width'], descriptor['body']['height'])

    def generate(self):
        objects = []
        objects.append(exporter.Label(name=self.name, position=(0.0, 0.0), thickness=self.thickness, font=self.font))

        borders = (self.body[0] / 2.0, self.body[1] / 2.0)
        borderDeltaX = borders[0] - self.sideSize[0] / 2.0 - self.thickness / 2.0
        if borderDeltaX < self.gap:
            borders = (borders[0] + (self.gap - borderDeltaX), borders[1])

        pads = []
        pads.append(exporter.SmdPad(1, self.coreSize, self.coreOffset))
        pads.append(exporter.SmdPad(2, self.sideSize, (self.sideOffset[0], self.sideOffset[1])))
        pads.append(exporter.SmdPad(2, self.sideSize, (self.sideOffset[0], -self.sideOffset[1])))
        objects += pads

        lines = []
        lines.append(exporter.Line((borders[0], borders[1]), (-borders[0], borders[1]), self.thickness))
        lines.append(exporter.Line((-borders[0], borders[1]), (-borders[0], -borders[1]), self.thickness))
        lines.append(exporter.Line((-borders[0], -borders[1]), (borders[0], -borders[1]), self.thickness))
        lines.append(exporter.Line((borders[0], -borders[1]), (borders[0], borders[1]), self.thickness))

        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [objects.extend(processFunc(line)) for line in lines]

        return objects


class IPX(IpxFootprint):
    def __init__(self, spec, descriptor):
        IpxFootprint.__init__(self=self, spec=spec, descriptor=descriptor,
                coreSize=(1.0, 1.0), coreOffset=(1.5, 0.0), sideSize=(2.2, 1.05), sideOffset=(0, 1.475))


class MemoryCard(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            exporter.AbstractPad.__init__(self, number, (diameter, diameter), position, diameter,
                    exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                    exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'], description=MemoryCard.describe(descriptor))

        self.signalPadCount = 9
        self.signalPadSize = (0.7, 1.6)
        self.signalpadPitch = -1.1
        self.signalPadOffset = (2.25, -10.5)

        # Top left pad, top right pad, bottom left pad, bottom right pad
        self.mountPadSizes = ((1.2, 1.4), (1.6, 1.4), (1.2, 2.2), (1.2, 2.2))
        self.mountPadOffsets = ((-7.75, -10.0), (6.85, -10.0), (-7.75, -0.4), (7.75, -0.4))

        self.mountHoleDiameter = 1.0
        self.mountHoleOffsets = ((-4.93, 0.0), (3.05, 0.0))

        self.bodySize = (14.7, 14.5)
        self.bodyOffset = (0.0, -2.75)
        self.labelOffset = (0.0, -2.0)

        self.font = spec['font']
        self.gap = spec['gap']
        self.thickness = spec['thickness']

    def generate(self):
        objects = []

        bodyLeft = -self.bodySize[0] / 2.0 + self.bodyOffset[0]
        bodyRight = self.bodySize[0] / 2.0 + self.bodyOffset[0]
        bodyTop = self.bodySize[1] / 2.0 + self.bodyOffset[1]
        bodyBottom = -self.bodySize[1] / 2.0 + self.bodyOffset[1]

        dotMarkRadius = self.thickness / 2.0
        dotMarkOffset = (self.signalPadOffset[0], self.signalPadOffset[1] - (self.signalPadSize[1] / 2.0 + self.gap
                + self.thickness))

        objects.append(exporter.Label(name=self.name, position=(0.0, 0.0), thickness=self.thickness, font=self.font))
        objects.append(exporter.Circle(dotMarkOffset, dotMarkRadius, self.thickness))

        pads = []

        # Mounting pads
        for i in range(0, len(self.mountPadSizes)):
            pads.append(exporter.SmdPad('', self.mountPadSizes[i], self.mountPadOffsets[i]))

        # Mounting holes
        for i in range(0, len(self.mountHoleOffsets)):
            pads.append(MemoryCard.MountHole('', self.mountHoleOffsets[i], self.mountHoleDiameter))

        # Signal pads
        for i in range(0, self.signalPadCount):
            x = self.signalPadOffset[0] + self.signalpadPitch * i
            y = self.signalPadOffset[1]
            pads.append(exporter.SmdPad(i + 1, self.signalPadSize, (x, y)))

        objects += pads

        lines = []
        lines.append(exporter.Line((bodyLeft, bodyTop), (bodyRight, bodyTop), self.thickness))
        lines.append(exporter.Line((bodyLeft, bodyBottom), (bodyRight, bodyBottom), self.thickness))
        lines.append(exporter.Line((bodyLeft, bodyTop), (bodyLeft, bodyBottom), self.thickness))
        lines.append(exporter.Line((bodyRight, bodyTop), (bodyRight, bodyBottom), self.thickness))

        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [objects.extend(processFunc(line)) for line in lines]

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


class AngularSmaFootprint(exporter.Footprint):
    class SidePad(exporter.AbstractPad):
        def __init__(self, number, size, position, layer):
            exporter.AbstractPad.__init__(self, number, size, position, 0.0, exporter.AbstractPad.STYLE_RECT,
                    exporter.AbstractPad.FAMILY_SMD, layer, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor, space, innerSize, outerSize):
        exporter.Footprint.__init__(self, name=descriptor['title'], description='')

        self.space = space
        self.innerSize = innerSize
        self.outerSize = outerSize

        self.font = spec['font']
        self.gap = spec['gap']
        self.thickness = spec['thickness']

    def generate(self):
        objects = []
        objects.append(exporter.Label(name=self.name, position=(0.0, 0.0), thickness=self.thickness, font=self.font))

        borders = (
                self.space + self.outerSize[0] / 2.0 + self.thickness / 2.0 + self.gap,
                self.innerSize[1] / 2.0 + self.thickness / 2.0 + self.gap
        )
        yOuterBorder = self.innerSize[1] / 2.0 - self.thickness / 2.0

        objects.append(AngularSmaFootprint.SidePad(1, self.innerSize, (0.0, 0.0),
                exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad(2, self.outerSize, (self.space, 0.0),
                exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad(2, self.outerSize, (-self.space, 0.0),
                exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad(2, self.outerSize, (self.space, 0.0),
                exporter.AbstractPad.LAYERS_BACK))
        objects.append(AngularSmaFootprint.SidePad(2, self.outerSize, (-self.space, 0.0),
                exporter.AbstractPad.LAYERS_BACK))

        objects.append(exporter.Line((borders[0], yOuterBorder), (borders[0], -borders[1]), self.thickness))
        objects.append(exporter.Line((-borders[0], yOuterBorder), (-borders[0], -borders[1]), self.thickness))
        objects.append(exporter.Line((borders[0], -borders[1]), (-borders[0], -borders[1]), self.thickness))

        return objects


class SMA:
    def __init__(self, spec, descriptor):
        if descriptor['body']['angular']:
            self.impl = AngularSmaFootprint(spec=spec, descriptor=descriptor,
                    space=2.65, innerSize=(1.5, 4.6), outerSize=(2.0, 4.6))
        else:
            raise Exception() # TODO Add more variants

        self.name = self.impl.name
        self.description = self.impl.description
        self.model = self.impl.model

    def generate(self):
        return self.impl.generate()


class MiniUSB(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            exporter.AbstractPad.__init__(self, number, (diameter, diameter), position, diameter,
                    exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                    exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'], description=MiniUSB.describe(descriptor))

        self.padOffset = 3.05
        self.padPitch = 0.8
        self.padSize = (2.3, 0.5)
        self.holdOffset = 4.4
        self.frontHold = -2.95
        self.backHold = 2.55
        self.holdSize = (2.5, 2.0)
        self.holeDiameter = 0.9
        self.holeSpacing = 2.2
        self.bodySize = (9.3, 7.7)
        self.bodyOffset = 1.35

        self.font = spec['font']
        self.gap = spec['gap']
        self.thickness = spec['thickness']

    def generate(self):
        objects = []
        borders = (self.bodySize[0] / 2.0, self.bodySize[1] / 2.0)
        dotMarkRadius = self.thickness / 2.0
        dotMarkOffset = (self.padOffset + self.padSize[0] / 2.0 + self.gap + self.thickness, -2.0 * self.padPitch)

        objects.append(exporter.Label(name=self.name, position=(0.0, 0.0), thickness=self.thickness, font=self.font))
        objects.append(exporter.Circle(dotMarkOffset, dotMarkRadius, self.thickness))

        pads = []

        for i in range(0, 5):
            yOffset = float(i - 2) * self.padPitch
            pads.append(exporter.SmdPad(i + 1, self.padSize, (self.padOffset, yOffset)))

        pads.append(exporter.SmdPad('', self.holdSize, (self.backHold, self.holdOffset)))
        pads.append(exporter.SmdPad('', self.holdSize, (self.backHold, -self.holdOffset)))
        pads.append(exporter.SmdPad('', self.holdSize, (self.frontHold, self.holdOffset)))
        pads.append(exporter.SmdPad('', self.holdSize, (self.frontHold, -self.holdOffset)))

        pads.append(MiniUSB.MountHole('', (0.0, self.holeSpacing), self.holeDiameter))
        pads.append(MiniUSB.MountHole('', (0.0, -self.holeSpacing), self.holeDiameter))

        objects += pads

        lines = []
        lines.append(exporter.Line((borders[0] - self.bodyOffset, borders[1]),
                (-borders[0] - self.bodyOffset, borders[1]), self.thickness))
        lines.append(exporter.Line((-borders[0] - self.bodyOffset, borders[1]),
                (-borders[0] - self.bodyOffset, -borders[1]), self.thickness))
        lines.append(exporter.Line((-borders[0] - self.bodyOffset, -borders[1]),
                (borders[0] - self.bodyOffset, -borders[1]), self.thickness))
        lines.append(exporter.Line((borders[0] - self.bodyOffset, -borders[1]),
                (borders[0] - self.bodyOffset, borders[1]), self.thickness))

        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [objects.extend(processFunc(line)) for line in lines]

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


class USB:
    def __init__(self, spec, descriptor):
        if descriptor['body']['size'] == 'mini' and descriptor['body']['type'] == 'b':
            self.impl = MiniUSB(spec, descriptor)
        else:
            raise Exception() # TODO Add more variants

        self.name = self.impl.name
        self.description = self.impl.description
        self.model = self.impl.model

    def generate(self):
        return self.impl.generate()


# Aliases

class EastRisingHB(FlexibleFlatCableConnector):
    def __init__(self, spec, descriptor):
        FlexibleFlatCableConnector.__init__(self, spec, descriptor)


class EastRisingHT(FlexibleFlatCableConnector):
    def __init__(self, spec, descriptor):
        FlexibleFlatCableConnector.__init__(self, spec, descriptor)


class Molex52271(FlexibleFlatCableConnector):
    def __init__(self, spec, descriptor):
        FlexibleFlatCableConnector.__init__(self, spec, descriptor)


types = [
        FlexibleFlatCableConnector,
        IPX,
        MemoryCard,
        SMA,
        USB,
        EastRisingHB,
        EastRisingHT,
        Molex52271
]
