#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import model
import primitives


class QFP:
    BODY_CHAMFER = primitives.hmils(0.1)
    BODY_OFFSET_Z = primitives.hmils(0.1)
    BODY_ROUNDNESS = primitives.hmils(0.5)

    BAND_OFFSET = primitives.hmils(0.0)
    BAND_WIDTH = primitives.hmils(0.1)

    MARK_RADIUS = primitives.hmils(0.5)

    CHAMFER_RESOLUTION = 1
    LINE_RESOLUTION    = 1
    EDGE_RESOLUTION    = 3


    def __init__(self):
        pass

    def generatePackagePins(self, pattern, count, size, offset, pitch):
        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=pattern, name='Pin{:d}'.format(number))
            pin.translate([x, y, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        pins = []

        # Horizontal pins
        y = size[1] / 2.0 + offset
        for i in range(0, count[0]):
            x = pitch * (i - (count[0] - 1) / 2.0)
            pins.append(makePin(x, y, math.pi, i + 1))
            pins.append(makePin(-x, -y, 0.0, i + 1 + count[0] + count[1]))

        # Vertical pins
        x = size[0] / 2.0 + offset
        for i in range(0, count[1]):
            y = pitch * (i - (count[1] - 1) / 2.0)
            pins.append(makePin(x, -y, math.pi / 2.0, i + 1 + count[0]))
            pins.append(makePin(-x, y, -math.pi / 2.0, i + 1 + count[0] * 2 + count[1]))

        return pins

    def generate(self, materials, templates, descriptor):
        bodySize = primitives.hmils(descriptor['body']['size'])
        pinCount = [descriptor['pins']['columns'], descriptor['pins']['rows']]
        pinHeight = bodySize[2] / 2.0 + QFP.BODY_OFFSET_Z
        pinPitch = primitives.hmils(descriptor['pins']['pitch'])
        pinShape = primitives.hmils(descriptor['pins']['shape'])
        markOffset = self.calcMarkOffset(pinCount, pinPitch)

        bandWidthProj = QFP.BAND_WIDTH * math.sqrt(0.5)
        bodySlope = math.atan(2.0 * bandWidthProj / bodySize[2])
        pinOffset = pinShape[1] * math.sin(bodySlope) / 2.0

        bodyTransform = model.Transform()
        bodyTransform.translate([0.0, 0.0, pinHeight])

        bodyMesh, markMesh = primitives.makeRoundedBox(
                size=bodySize,
                roundness=QFP.BODY_ROUNDNESS,
                chamfer=QFP.BODY_CHAMFER,
                edgeResolution=QFP.EDGE_RESOLUTION,
                lineResolution=QFP.LINE_RESOLUTION,
                band=QFP.BAND_OFFSET,
                bandWidth=QFP.BAND_WIDTH,
                markRadius=QFP.MARK_RADIUS,
                markOffset=markOffset,
                markResolution=24)

        if 'Body' in materials:
            bodyMesh.appearance().material = materials['Body']
        bodyMesh.apply(bodyTransform)
        bodyMesh.rename('Body')

        if 'Mark' in materials:
            markMesh.appearance().material = materials['Mark']
        markMesh.apply(bodyTransform)
        markMesh.rename('Mark')

        pinMesh = primitives.makePinMesh(
                pinShapeSize=pinShape,
                pinHeight=pinHeight + pinShape[1] * math.cos(bodySlope) / 2.0,
                pinLength=primitives.hmils(descriptor['pins']['length']) + pinOffset,
                endSlope=bodySlope,
                chamferResolution=QFP.CHAMFER_RESOLUTION,
                edgeResolution=QFP.EDGE_RESOLUTION)
        if 'Pin' in materials:
            pinMesh.appearance().material = materials['Pin']

        pins = self.generatePackagePins(
                pattern=pinMesh,
                count=pinCount,
                size=bodySize,
                offset=bandWidthProj - pinOffset,
                pitch=pinPitch)

        return pins + [bodyMesh] + [markMesh]

    def calcMarkOffset(self, count, pitch):
        firstPinOffset = (numpy.asfarray(count) - 1.0) * pitch / 2.0
        return -firstPinOffset + pitch / 2.0


types = [QFP]
