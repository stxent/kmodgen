#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# conncetors.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class FlexibleFlatCableConnector(exporter.Footprint):
    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=FlexibleFlatCableConnector.describe(descriptor), spec=spec)

        self.mountPadSize = numpy.array([descriptor['pads']['mountWidth'], descriptor['pads']['mountHeight']])
        self.mountPadSpacing = numpy.array([
                descriptor['mount']['horizontalSpacing'],
                descriptor['mount']['verticalSpacing']
        ])
        self.signalPadSize = numpy.array([descriptor['pads']['width'], descriptor['pads']['height']])
        self.signalPadOffset = descriptor['pads']['offset']
        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.bodyHeight = descriptor['body']['height']
        self.bodyWidthIncrease = descriptor['body']['widthIncrease']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, self.center, self.thickness, self.font))

        totalPadsWidth = float(self.count - 1) * self.pitch

        # First pin mark
        dotMarkPosition = numpy.array([
                -totalPadsWidth / 2.0,
                -(self.signalPadOffset + self.signalPadSize[1] / 2.0 + self.gap + self.thickness)
        ])
        silkscreen.append(exporter.Circle(dotMarkPosition, self.thickness / 2.0, self.thickness))

        # Mounting pads
        mountPadOffset = self.mountPadSpacing + numpy.array([totalPadsWidth / 2.0, self.signalPadOffset])
        pads.append(exporter.SmdPad('', self.mountPadSize, mountPadOffset * numpy.array([+1.0, -1.0])))
        pads.append(exporter.SmdPad('', self.mountPadSize, mountPadOffset * numpy.array([-1.0, -1.0])))

        # Signal pads
        for i in range(0, self.count):
            x = -totalPadsWidth / 2.0 + i * self.pitch
            pads.append(exporter.SmdPad(i + 1, self.signalPadSize, (x, -self.signalPadOffset)))

        # Body outline
        topCorner = numpy.array([totalPadsWidth / 2.0 + self.bodyWidthIncrease, self.bodyHeight / 2.0])
        outline = exporter.Rect(topCorner, -topCorner, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor.keys():
            return descriptor['description']
        else:
            round1f = lambda x: '{:d}'.format(x) if int(x * 10) == int(x) * 10 else '{:.1f}'.format(x)
            pitchStr = round1f(descriptor['pins']['pitch'])
            return 'FFC/FPC connector, {:s} mm pitch, surface mount, {:s} contact style, {:d} circuits'.format(
                    pitchStr, descriptor['pins']['style'], descriptor['pins']['count'])


class IpxFootprint(exporter.Footprint):
    def __init__(self, spec, descriptor, coreSize, coreOffset, sideSize, sideOffset):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description='Miniature RF connector for high-frequency signals', spec=spec)

        self.coreOffset, self.coreSize = numpy.array(coreOffset), numpy.array(coreSize)
        self.sideOffset, self.sideSize = numpy.array(sideOffset), numpy.array(sideSize)
        self.bodySize = numpy.array([descriptor['body']['width'], descriptor['body']['height']])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        pads.append(exporter.SmdPad(1, self.coreSize, self.coreOffset))
        pads.append(exporter.SmdPad(2, self.sideSize, self.sideOffset * numpy.array([+1.0, +1.0])))
        pads.append(exporter.SmdPad(2, self.sideSize, self.sideOffset * numpy.array([+1.0, -1.0])))

        # Body outline
        outlineDeltaX = (self.bodySize[0] - self.sideSize[0] - self.thickness) / 2.0
        outlineDeltaX = self.gap - outlineDeltaX if outlineDeltaX < self.gap else 0.0
        outlineSize = numpy.array([self.bodySize[0] / 2.0 + outlineDeltaX, self.bodySize[1] / 2.0])
        outline = exporter.Rect(outlineSize, -outlineSize, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        return silkscreen + pads


class IPX(IpxFootprint):
    def __init__(self, spec, descriptor):
        IpxFootprint.__init__(self=self, spec=spec, descriptor=descriptor,
                coreSize=(1.0, 1.0), coreOffset=(1.5, 0.0), sideSize=(2.2, 1.05), sideOffset=(0.0, 1.475))


class MemoryCard(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            exporter.AbstractPad.__init__(self, number, (diameter, diameter), position, diameter,
                    exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                    exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=MemoryCard.describe(descriptor), spec=spec)

        self.signalPadCount = 9
        self.signalPadSize = numpy.array([0.7, 1.6])
        self.signalpadPitch = -1.1
        self.signalPadOffset = numpy.array([2.25, -10.5])

        # Top left pad, top right pad, bottom left pad, bottom right pad
        self.mountPadSizes = ((1.2, 1.4), (1.6, 1.4), (1.2, 2.2), (1.2, 2.2))
        self.mountPadOffsets = ((-7.75, -10.0), (6.85, -10.0), (-7.75, -0.4), (7.75, -0.4))

        self.mountHoleDiameter = 1.0
        self.mountHoleOffsets = ((-4.93, 0.0), (3.05, 0.0))

        self.bodySize = numpy.array([14.7, 14.5])
        self.bodyOffset = numpy.array([0.0, -2.75])
        self.labelOffset = numpy.array([0.0, -2.0])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # First pin mark
        dotMarkPosition = self.signalPadOffset + numpy.array([0.0, self.signalPadSize[1] / 2.0
                + self.gap + self.thickness])
        silkscreen.append(exporter.Circle(dotMarkPosition, self.thickness / 2.0, self.thickness))

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

        # Body outline
        topCorner = self.bodySize / 2.0
        outline = exporter.Rect(topCorner + self.bodyOffset, -topCorner + self.bodyOffset, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


class AngularSmaFootprint(exporter.Footprint):
    class SidePad(exporter.AbstractPad):
        def __init__(self, number, size, position, layer):
            exporter.AbstractPad.__init__(self, number, size, position, 0.0, exporter.AbstractPad.STYLE_RECT,
                    exporter.AbstractPad.FAMILY_SMD, layer, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor, space, innerSize, outerSize):
        exporter.Footprint.__init__(self, name=descriptor['title'],
                description=AngularSmaFootprint.describe(descriptor), spec=spec)

        self.space = space
        self.innerSize = numpy.array(innerSize)
        self.outerSize = numpy.array(outerSize)

    @staticmethod
    def makePolyLine(points, thickness, layer):
        if len(points) < 2:
            raise Exception()
        lines = []
        for seg in range(0, len(points) - 1):
            lines.append(exporter.Line(points[seg], points[seg + 1], thickness, layer))
        return lines

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
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

        # Body outline
        xOutline = self.gap + self.thickness / 2.0 + self.outerSize[0] / 2.0 + self.space
        yBottomOutline = (self.innerSize[1] - self.thickness) / 2.0
        yTopOutline = -(self.innerSize[1] + self.thickness) / 2.0 - self.gap

        outlinePoints = [
                (xOutline, yBottomOutline),
                (xOutline, yTopOutline),
                (-xOutline, yTopOutline),
                (-xOutline, yBottomOutline)
        ]
        objects.extend(AngularSmaFootprint.makePolyLine(outlinePoints, self.thickness, exporter.Layer.SILK_FRONT))
        objects.extend(AngularSmaFootprint.makePolyLine(outlinePoints, self.thickness, exporter.Layer.SILK_BACK))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor.keys() else ''


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
        exporter.Footprint.__init__(self, name=descriptor['title'], description=MiniUSB.describe(descriptor), spec=spec)

        self.padOffset = 3.05
        self.padPitch = 0.8
        self.padSize = numpy.array([2.3, 0.5])
        self.mountPadOffset = 4.4
        self.frontMountPad = -2.95
        self.backMountPad = 2.55
        self.mountPadSize = numpy.array([2.5, 2.0])
        self.mountHoleDiameter = 0.9
        self.mountHoleSpacing = 2.2
        self.bodySize = numpy.array([9.3, 7.7])
        self.bodyOffset = numpy.array([1.35, 0.0])

    def generate(self):
        silkscreen, pads = [], []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # First pin mark
        dotMarkPosition = (self.padOffset + self.padSize[0] / 2.0 + self.gap + self.thickness, -2.0 * self.padPitch)
        objects.append(exporter.Circle(dotMarkPosition, self.thickness / 2.0, self.thickness))

        # Pads
        for i in range(0, 5):
            y = float(i - 2) * self.padPitch
            pads.append(exporter.SmdPad(i + 1, self.padSize, (self.padOffset, y)))

        pads.append(exporter.SmdPad('', self.mountPadSize, (self.backMountPad, self.mountPadOffset)))
        pads.append(exporter.SmdPad('', self.mountPadSize, (self.backMountPad, -self.mountPadOffset)))
        pads.append(exporter.SmdPad('', self.mountPadSize, (self.frontMountPad, self.mountPadOffset)))
        pads.append(exporter.SmdPad('', self.mountPadSize, (self.frontMountPad, -self.mountPadOffset)))

        pads.append(MiniUSB.MountHole('', (0.0, self.mountHoleSpacing), self.mountHoleDiameter))
        pads.append(MiniUSB.MountHole('', (0.0, -self.mountHoleSpacing), self.mountHoleDiameter))

        topCorner = self.bodySize / 2.0
        outline = exporter.Rect(topCorner - self.bodyOffset, -topCorner - self.bodyOffset, self.thickness)
        processFunc = lambda x: exporter.collideLine(x, pads, self.thickness, self.gap)
        [silkscreen.extend(processFunc(line)) for line in outline.lines]

        return silkscreen + pads

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
