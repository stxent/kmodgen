#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import model
import primitives


class SOP:
    def __init__(self):
        pass

    def generatePackagePins(self, pattern, count, size, offset, pitch):
        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=pattern, name='Pin{:d}'.format(number))
            pin.translate([x, y, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        rows = int(count / 2)
        pins = []

        # Pins
        y = size[1] / 2.0 + offset
        for i in range(0, rows):
            x = pitch * (i - (rows - 1) / 2.0)
            pins.append(makePin(x, y, math.pi, i + 1 + rows))
            pins.append(makePin(-x, -y, 0.0, i + 1))

        return pins

    def generate(self, materials, templates, descriptor):
        BODY_OFFSET_Z = primitives.hmils(0.1)
        BAND_OFFSET = primitives.hmils(0.0)
        BAND_WIDTH = primitives.hmils(0.1)
        CHAMFER = primitives.hmils(0.1)

        bodySize = primitives.hmils(descriptor['body']['size'])
        pinHeight = bodySize[2] / 2.0 + BODY_OFFSET_Z

        bandWidthProj = BAND_WIDTH * math.sqrt(0.5)
        bodySlope = 2.0 * bandWidthProj / bodySize[2]
        pinOffset = bandWidthProj - bodySlope * primitives.hmils(descriptor['pins']['shape'][1]) / 2.0

        bodyTransform = model.Transform()
        bodyTransform.rotate([0.0, 0.0, 1.0], math.pi)
        bodyTransform.translate([0.0, 0.0, pinHeight])

        bodyMesh = primitives.makeSlopedBox(
                size=bodySize,
                chamfer=CHAMFER,
                slope=math.pi / 4.0,
                slopeHeight=bodySize[2] / 5.0,
                seamResolution=3,
                lineResolution=1,
                band=BAND_OFFSET,
                bandWidth=BAND_WIDTH)

        if 'Body' in materials:
            bodyMesh.appearance().material = materials['Body']
        bodyMesh.apply(bodyTransform)
        bodyMesh.rename('Body')

        pinMesh = primitives.makePinMesh(
                pinShapeSize=primitives.hmils(descriptor['pins']['shape']),
                pinHeight=pinHeight,
                pinLength=primitives.hmils(descriptor['pins']['length']),
                endSlope=math.atan(bodySlope),
                chamferSegments=1,
                slopeSegments=3)
        if 'Pin' in materials:
            pinMesh.appearance().material = materials['Pin']

        pins = self.generatePackagePins(
                pattern=pinMesh,
                count=descriptor['pins']['count'],
                size=bodySize,
                offset=pinOffset,
                pitch=primitives.hmils(descriptor['pins']['pitch']))

        return pins + [bodyMesh]


types = [SOP]
