#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import re

from wrlconv import model

def lookup(meshList, meshName):
    found = []
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            found.append(entry)
    return found

def metricToImperial(value):
    return value / 2.54 #Convert millimeters to hundreds of mils


class QuadFlatPackage:
    @staticmethod
    def buildPackageBody(materials, modelBody, modelMark, modelPin, count, size, pitch, name):
        DEFAULT_WIDTH = metricToImperial(5.0)
        margin = (size[0] / 2., size[1] / 2.)

        offset = (pitch / 2. if count[0] % 2 == 0 else pitch, pitch / 2. if count[1] % 2 == 0 else pitch)
        dot = ((-count[0] / 2. + 1.5) * pitch - offset[0], (-count[1] / 2. + 1.5) * pitch - offset[1])

        cornerTranslation = ((size[0] - DEFAULT_WIDTH) / 2., (size[1] - DEFAULT_WIDTH) / 2.)
        corners = [model.Transform(), model.Transform(), model.Transform(), model.Transform()]
        center = model.Transform()
        center.translate([dot[0], dot[1], 0.])
        corners[0].translate([ cornerTranslation[0],  cornerTranslation[1], 0.])
        corners[1].translate([-cornerTranslation[0],  cornerTranslation[1], 0.])
        corners[2].translate([ cornerTranslation[0], -cornerTranslation[1], 0.])
        corners[3].translate([-cornerTranslation[0], -cornerTranslation[1], 0.])
        transforms = [model.Transform()] + [center] + corners
        body = copy.deepcopy(modelBody)
        body.applyTransforms(transforms)
        body.translate([0., 0., 0.001])
        if "Body" in materials.keys():
            body.appearance().material = materials["Body"]

        mark = copy.deepcopy(modelMark)
        mark.translate([dot[0], dot[1], 0.001])
        if "Mark" in materials.keys():
            mark.appearance().material = materials["Mark"]

        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=modelPin, name="%s%uPin%u" % (name, count[0] * 2 + count[1] * 2, number))
            pin.translate([x, y, 0.001])
            pin.rotate([0., 0., 1.], angle * math.pi / 180.)
            if "Pin" in materials.keys():
                pin.appearance().material = materials["Pin"]
            return pin

        pins = []
        for i in range(0, count[0]):
            x = (i - count[0] / 2 + 1) * pitch - offset[0]
            y = margin[1]

            pins.append(makePin(x, y, 180., i + 1))
            pins.append(makePin(-x, -y, 0., i + 1 + count[0] + count[1]))
        for i in range(0, count[1]):
            x = margin[0]
            y = (i - count[1] / 2 + 1) * pitch - offset[1]

            pins.append(makePin(x, -y, 90., i + 1 + count[0]))
            pins.append(makePin(-x, y, -90., i + 1 + count[0] * 2 + count[1]))

        return [body, mark] + pins

    @staticmethod
    def build(materials, templates, descriptor):
        qfpBody = lookup(templates, "PatQFPBody")[0].parent
        qfpBodyMark = lookup(templates, "PatQFPBody")[1].parent

        qfpNarrowPin = lookup(templates, "PatQFPNarrowPin")[0].parent
        qfpWidePin = lookup(templates, "PatQFPWidePin")[0].parent

        regions = [
                ((( 0.5,  0.5, 1.0), (-0.5, -0.5, -1.0)), 1),
                ((( 1.5,  1.5, 1.0), ( 0.5,  0.5, -1.0)), 2),
                (((-1.5,  1.5, 1.0), (-0.5,  0.5, -1.0)), 3),
                ((( 1.5, -1.5, 1.0), ( 0.5, -0.5, -1.0)), 4),
                (((-1.5, -1.5, 1.0), (-0.5, -0.5, -1.0)), 5)]
        qfpAttributedBody = model.AttributedMesh(name="QFPBody", regions=regions)
        qfpAttributedBody.append(qfpBody)
        qfpAttributedBody.visualAppearance = qfpBody.appearance()

        if descriptor["pins"]["pitch"] >= 0.65:
            modelPin = qfpWidePin
        else:
            modelPin = qfpNarrowPin

        return QuadFlatPackage.buildPackageBody(
                materials,
                qfpAttributedBody, qfpBodyMark, modelPin,
                (descriptor["pins"]["columns"], descriptor["pins"]["rows"]),
                (metricToImperial(descriptor["body"]["width"]), metricToImperial(descriptor["body"]["length"])),
                metricToImperial(descriptor["pins"]["pitch"]),
                descriptor["title"])


types = [QuadFlatPackage]
