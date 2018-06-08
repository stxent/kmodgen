#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sop.py
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


class SOP:
    def __init__(self):
        pass

    def generatePackageBody(self, materials, modelBody, modelMark, modelPin, markOffset, count, size, pitch, name):
        DEFAULT_WIDTH = model.metricToImperial(2.0)

        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=modelPin, name='{:s}Pin{:d}'.format(name, number))
            pin.translate([x, y, 0.001])
            pin.rotate([0.0, 0.0, 1.0], angle * math.pi / 180.0)
            if 'Pin' in materials.keys():
                pin.appearance().material = materials['Pin']
            return pin

        rows = int(count / 2)
        firstPinOffset = float(rows - 1) * pitch / 2.0
        dotPosition = markOffset - size[0:2] / 2.0

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

        # Pins
        y = size[1] / 2.0
        for i in range(0, rows):
            x = float(i) * pitch - firstPinOffset
            pins.append(makePin(x, y, 180.0, i + 1 + rows))
            pins.append(makePin(-x, -y, 0.0, i + 1))

        return [body, mark] + pins

    def generate(self, materials, templates, descriptor):
        regions = [
                (((0.15,  0.15, 1.0), (-0.15, -0.15, -1.0)), 1),
                ((( 1.0,  1.0,  1.0), ( 0.15,  0.15, -1.0)), 2),
                (((-1.0,  1.0,  1.0), (-0.15,  0.15, -1.0)), 3),
                ((( 1.0, -1.0,  1.0), ( 0.15, -0.15, -1.0)), 4),
                (((-1.0, -1.0,  1.0), (-0.15, -0.15, -1.0)), 5)]

        referenceObject = None

        if descriptor['package']['subtype'] == 'SO':
            soBody = lookup(templates, 'PatSOBody')[0].parent
            soBodyMark = lookup(templates, 'PatSOBody')[1].parent
            soPin = lookup(templates, 'PatSOPin')[0].parent

            # Modified SO models
            soAttributedBody = model.AttributedMesh(name='SOBody', regions=regions)
            soAttributedBody.append(soBody)
            soAttributedBody.visualAppearance = soBody.appearance()

            referenceObject = (soAttributedBody, soBodyMark, soPin, (0.75, 1.0))
        elif descriptor['package']['subtype'] == 'TSSOP':
            tssopBody = lookup(templates, 'PatTSSOPBody')[0].parent
            tssopBodyMark = lookup(templates, 'PatTSSOPBody')[1].parent
            tssopPin = lookup(templates, 'PatTSSOPPin')[0].parent

            # TSSOP model uses same regions
            tssopAttributedBody = model.AttributedMesh(name='TSSOPBody', regions=regions)
            tssopAttributedBody.append(tssopBody)
            tssopAttributedBody.visualAppearance = tssopBody.appearance()

            referenceObject = (tssopAttributedBody, tssopBodyMark, tssopPin, (0.75, 0.75))
        else:
            raise Exception()

        return self.generatePackageBody(
                materials,
                referenceObject[0], referenceObject[1], referenceObject[2],
                numpy.array(model.metricToImperial(referenceObject[3])),
                descriptor['pins']['count'],
                numpy.array(model.metricToImperial(descriptor['body']['size'])),
                model.metricToImperial(descriptor['pins']['pitch']),
                descriptor['title'])


types = [SOP]
