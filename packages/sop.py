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
    def buildPackageBody(modelBody, modelHole, modelPin, holeOffset, size, pitch, count, name):
        DEFAULT_WIDTH = metricToImperial(2.0)

        bodyDelta = ((size[0] - DEFAULT_WIDTH) / 2., (size[1] - DEFAULT_WIDTH) / 2.)

        sideCount = count / 2
        offset = pitch / 2. if sideCount % 2 == 0 else pitch
        dot = (-(size[0] / 2. - holeOffset[0]), -(size[1] / 2. - holeOffset[1]))
    
        corners = [model.Transform(), model.Transform(), model.Transform(), model.Transform()]
        center = model.Transform()
        center.translate([dot[0], dot[1], 0.])
        corners[0].translate([ bodyDelta[0],  bodyDelta[1], 0.])
        corners[1].translate([-bodyDelta[0],  bodyDelta[1], 0.])
        corners[2].translate([ bodyDelta[0], -bodyDelta[1], 0.])
        corners[3].translate([-bodyDelta[0], -bodyDelta[1], 0.])
        transforms = [model.Transform()] + [center] + corners
        body = copy.deepcopy(modelBody)
        body.applyTransforms(transforms)
        body.translate([0., 0., 0.001])
#         body.appearance().normals = debugNormals
#         body.appearance().smooth = debugSmoothShading
        
        hole = copy.deepcopy(modelHole)
        hole.translate([dot[0], dot[1], 0.001])
        hole.appearance().normals = debugNormals
        hole.appearance().smooth = debugSmoothShading
    
        def makePin(x, y, angle, number):
            pin = model.Mesh(parent=modelPin, name="%s%uPin%u" % (name, count, number))
            pin.translate([x, y, 0.001])
            pin.rotate([0., 0., 1.], angle * math.pi / 180.)
            pin.appearance().normals = debugNormals
            pin.appearance().smooth = debugSmoothShading
            return pin
    
        pins = []
        for i in range(0, sideCount):
            x = (i - sideCount / 2 + 1) * pitch - offset
            y = size[1] / 2.
    
            pins.append(makePin(x, y, 180., i + 1 + sideCount))
            pins.append(makePin(-x, -y, 0., i + 1))
    
        return [body, hole] + pins

    @staticmethod
    def build(materials, patterns, descriptor):
        soRegions = [
                (((0.15, 0.15, 1.0), (-0.15, -0.15, -1.0)), 1),
                (((1.0, 1.0, 1.0), (0.15, 0.15, -1.0)), 2),
                (((-1.0, 1.0, 1.0), (-0.15, 0.15, -1.0)), 3),
                (((1.0, -1.0, 1.0), (0.15, -0.15, -1.0)), 4),
                (((-1.0, -1.0, 1.0), (-0.15, -0.15, -1.0)), 5)]
        
        referenceObject = None

        if descriptor["package"]["subtype"] == "SO":
            soBody = lookup(patterns, "PatSOBody")[0].parent
            soBodyHole = lookup(patterns, "PatSOBody")[1].parent
            soPin = lookup(patterns, "PatSOPin")[0].parent
            
            #Modified SO models
            soAttributedBody = model.AttributedMesh(name="SOBody", regions=soRegions)
            soAttributedBody.append(soBody)
            soAttributedBody.visualAppearance = soBody.appearance()
            
            referenceObject = (soAttributedBody, soBodyHole, soPin, (0.75, 0.5))
        elif descriptor["package"]["subtype"] == "TSSOP":
            tssopBody = lookup(patterns, "PatTSSOPBody")[0].parent
            tssopBodyHole = lookup(patterns, "PatTSSOPBody")[1].parent
            tssopPin = lookup(patterns, "PatTSSOPPin")[0].parent
            
            #TSSOP model uses same regions
            tssopAttributedBody = model.AttributedMesh(name="TSSOPBody", regions=soRegions)
            tssopAttributedBody.append(tssopBody)
            tssopAttributedBody.visualAppearance = tssopBody.appearance()
            
            referenceObject = (tssopAttributedBody, tssopBodyHole, tssopPin, (0.75, 0.75))
        else:
            raise Exception()

        return SmallOutlinePackage.buildPackageBody(
                referenceObject[0], referenceObject[1], referenceObject[2],
                (metricToImperial(referenceObject[3][0]), metricToImperial(referenceObject[3][1])),
                (metricToImperial(descriptor["body"]["length"]), metricToImperial(descriptor["body"]["width"])),
                metricToImperial(descriptor["pins"]["pitch"]),
                descriptor["pins"]["count"],
                descriptor["title"])


types = [SmallOutlinePackage]
