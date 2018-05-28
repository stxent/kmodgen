#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy
import re

from wrlconv import model

def lookup(meshList, meshName):
    found = []
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            found.append(entry)
    return found


class QuadFlatPackage:
    def __init__(self):
        pass

    def generatePackageBody(self, materials, modelBody, modelMark, modelPin, count, size, pitch, name):
        DEFAULT_WIDTH = model.metricToImperial(5.0)

        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=modelPin, name='{:s}Pin{:d}'.format(name, number))
            pin.translate([x, y, 0.001])
            pin.rotate([0.0, 0.0, 1.0], angle * math.pi / 180.0)
            if 'Pin' in materials.keys():
                pin.appearance().material = materials['Pin']
            return pin

        firstPinOffset = (numpy.asfarray(count) - 1.0) * pitch / 2.0
        dotPosition = -firstPinOffset + pitch / 2.0

        # Body
        cornerTranslation = (size - DEFAULT_WIDTH) / 2.0
        corners = [model.Transform(), model.Transform(), model.Transform(), model.Transform()]
        center = model.Transform()
        center.translate([dotPosition[0], dotPosition[1], 0.0])
        corners[0].translate([ cornerTranslation[0],  cornerTranslation[1], 0.0])
        corners[1].translate([-cornerTranslation[0],  cornerTranslation[1], 0.0])
        corners[2].translate([ cornerTranslation[0], -cornerTranslation[1], 0.0])
        corners[3].translate([-cornerTranslation[0], -cornerTranslation[1], 0.0])
        transforms = [model.Transform()] + [center] + corners
        body = copy.deepcopy(modelBody)
        body.applyTransforms(transforms)
        body.translate([0.0, 0.0, 0.001])
        if 'Body' in materials.keys():
            body.appearance().material = materials['Body']

        # First pin mark
        mark = copy.deepcopy(modelMark)
        mark.translate([dotPosition[0], dotPosition[1], 0.001])
        if 'Mark' in materials.keys():
            mark.appearance().material = materials['Mark']

        pins = []

        # Horizontal pins
        y = size[1] / 2.0
        for i in range(0, count[0]):
            x = float(i) * pitch - firstPinOffset[0]
            pins.append(makePin(x, y, 180.0, i + 1))
            pins.append(makePin(-x, -y, 0.0, i + 1 + count[0] + count[1]))

        # Vertical pins
        x = size[0] / 2.0
        for i in range(0, count[1]):
            y = float(i) * pitch - firstPinOffset[1]
            pins.append(makePin(x, -y, 90.0, i + 1 + count[0]))
            pins.append(makePin(-x, y, -90.0, i + 1 + count[0] * 2 + count[1]))

        return [body, mark] + pins

    def generate(self, materials, templates, descriptor):
        qfpBody = lookup(templates, 'PatQFPBody')[0].parent
        qfpBodyMark = lookup(templates, 'PatQFPBody')[1].parent

        qfpNarrowPin = lookup(templates, 'PatQFPNarrowPin')[0].parent
        qfpWidePin = lookup(templates, 'PatQFPWidePin')[0].parent

        regions = [
                ((( 0.5,  0.5, 1.0), (-0.5, -0.5, -1.0)), 1),
                ((( 1.5,  1.5, 1.0), ( 0.5,  0.5, -1.0)), 2),
                (((-1.5,  1.5, 1.0), (-0.5,  0.5, -1.0)), 3),
                ((( 1.5, -1.5, 1.0), ( 0.5, -0.5, -1.0)), 4),
                (((-1.5, -1.5, 1.0), (-0.5, -0.5, -1.0)), 5)]
        qfpAttributedBody = model.AttributedMesh(name='QFPBody', regions=regions)
        qfpAttributedBody.append(qfpBody)
        qfpAttributedBody.visualAppearance = qfpBody.appearance()

        if descriptor['pins']['pitch'] >= 0.65:
            modelPin = qfpWidePin
        else:
            modelPin = qfpNarrowPin

        return self.generatePackageBody(
                materials,
                qfpAttributedBody, qfpBodyMark, modelPin,
                numpy.array([descriptor['pins']['columns'], descriptor['pins']['rows']]),
                numpy.array(model.metricToImperial(descriptor['body']['size'])),
                numpy.array(model.metricToImperial(descriptor['pins']['pitch'])),
                descriptor['title'])


types = [QuadFlatPackage]
