#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import re

from wrlconv import model

debugNormals = False
debugSmoothShading = False

def lookup(meshList, meshName):
    found = []
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            found.append(entry)
    return found

def metricToImperial(value):
    return value / 2.54 #Convert millimeters to hundreds of mils


class SmallOutlinePackage:
    @staticmethod
    def buildPackageBody(materials, modelBody, modelMark, modelPin, markOffset, count, size, pitch, name):
        DEFAULT_WIDTH = metricToImperial(2.0)

        halfCount = count / 2
        offset = pitch / 2. if halfCount % 2 == 0 else pitch
        dot = (-(size[0] / 2. - markOffset[0]), -(size[1] / 2. - markOffset[1]))

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
        body.appearance().normals = debugNormals
        body.appearance().smooth = debugSmoothShading
        if "Body" in materials.keys():
            body.appearance().material = materials["Body"]

        mark = copy.deepcopy(modelMark)
        mark.translate([dot[0], dot[1], 0.001])
        mark.appearance().normals = debugNormals
        mark.appearance().smooth = debugSmoothShading
        if "Mark" in materials.keys():
            mark.appearance().material = materials["Mark"]

        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=modelPin, name="%s%uPin%u" % (name, count, number))
            pin.translate([x, y, 0.001])
            pin.rotate([0., 0., 1.], angle * math.pi / 180.)
            pin.appearance().normals = debugNormals
            pin.appearance().smooth = debugSmoothShading
            if "Pin" in materials.keys():
                pin.appearance().material = materials["Pin"]
            return pin

        pins = []
        for i in range(0, halfCount):
            x = (i - halfCount / 2 + 1) * pitch - offset
            y = size[1] / 2.

            pins.append(makePin(x, y, 180., i + 1 + halfCount))
            pins.append(makePin(-x, -y, 0., i + 1))

        return [body, mark] + pins

    @staticmethod
    def build(materials, templates, descriptor):
        regions = [
                ((( 0.15,  0.15, 1.0), (-0.15, -0.15, -1.0)), 1),
                ((( 1.0,   1.0,  1.0), ( 0.15,  0.15, -1.0)), 2),
                (((-1.0,   1.0,  1.0), (-0.15,  0.15, -1.0)), 3),
                ((( 1.0,  -1.0,  1.0), ( 0.15, -0.15, -1.0)), 4),
                (((-1.0,  -1.0,  1.0), (-0.15, -0.15, -1.0)), 5)]

        referenceObject = None

        if descriptor["package"]["subtype"] == "SO":
            soBody = lookup(templates, "PatSOBody")[0].parent
            soBodyMark = lookup(templates, "PatSOBody")[1].parent
            soPin = lookup(templates, "PatSOPin")[0].parent

            #Modified SO models
            soAttributedBody = model.AttributedMesh(name="SOBody", regions=regions)
            soAttributedBody.append(soBody)
            soAttributedBody.visualAppearance = soBody.appearance()

            referenceObject = (soAttributedBody, soBodyMark, soPin, (0.75, 0.5))
        elif descriptor["package"]["subtype"] == "TSSOP":
            tssopBody = lookup(templates, "PatTSSOPBody")[0].parent
            tssopBodyMark = lookup(templates, "PatTSSOPBody")[1].parent
            tssopPin = lookup(templates, "PatTSSOPPin")[0].parent

            #TSSOP model uses same regions
            tssopAttributedBody = model.AttributedMesh(name="TSSOPBody", regions=regions)
            tssopAttributedBody.append(tssopBody)
            tssopAttributedBody.visualAppearance = tssopBody.appearance()

            referenceObject = (tssopAttributedBody, tssopBodyMark, tssopPin, (0.75, 0.75))
        else:
            raise Exception()

        return SmallOutlinePackage.buildPackageBody(
                materials,
                referenceObject[0], referenceObject[1], referenceObject[2],
                (metricToImperial(referenceObject[3][0]), metricToImperial(referenceObject[3][1])),
                descriptor["pins"]["count"],
                (metricToImperial(descriptor["body"]["length"]), metricToImperial(descriptor["body"]["width"])),
                metricToImperial(descriptor["pins"]["pitch"]),
                descriptor["title"])


types = [SmallOutlinePackage]
