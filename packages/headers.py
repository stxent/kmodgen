#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2015 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import re

from wrlconv import model

debugNormals = False
debugSmoothShading = False

def lookup(meshList, meshName):
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            return entry
    raise Exception()

def metricToImperial(value):
    return value / 2.54 #Convert millimeters to hundreds of mils


class PinHeader:
    @staticmethod
    def buildHeaderBody(modelBody, modelEdge, modelPin, count, pitch, name):
        shift = pitch / 2. if count[1] > 1 else 0.

        body = model.Mesh(name="%s_%uBody" % (name, count[0] * count[1]))
        body.visualAppearance = modelBody.appearance()

        pins = []
        for i in range(0, count[0]):
            if i == 0:
                segment = copy.deepcopy(modelEdge)
                segment.rotate([0., 0., 1.], math.pi)
            elif i == count[0] - 1:
                segment = copy.deepcopy(modelEdge)
                segment.rotate([0., 0., 1.], 0.)
            else:
                segment = copy.deepcopy(modelBody)
            segment.translate([float(i) * pitch, shift, 0.])
            body.append(segment)

            pin = model.Mesh(parent=modelPin, name="%s_%uPin%u" % (name, count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, shift, 0.001])
            pin.appearance().normals = debugNormals
            pin.appearance().smooth = debugSmoothShading
            pins.append(pin)

        body.translate([0., 0., 0.001])
        body.optimize()
        body.appearance().normals = debugNormals
        body.appearance().smooth = debugSmoothShading

        return [body] + pins

    @staticmethod
    def build(materials, templates, descriptor):
        def eq(a, b):
            TOLERANCE = 0.001
            return a - TOLERANCE <= b <= a + TOLERANCE

        if descriptor["pins"]["rows"] == 1:
            if eq(descriptor["pins"]["pitch"], 2.0):
                pls2Body = lookup(templates, "PatPLS2Body").parent
                pls2EdgeBody = lookup(templates, "PatPLS2EdgeBody").parent
                pls2Pin = lookup(templates, "PatPLS2Pin").parent

                referenceObject = (pls2Body, pls2EdgeBody, pls2Pin)
            elif eq(descriptor["pins"]["pitch"], 2.54):
                plsBody = lookup(templates, "PatPLSBody").parent
                plsEdgeBody = lookup(templates, "PatPLSEdgeBody").parent
                plsPin = lookup(templates, "PatPLSPin").parent

                referenceObject = (plsBody, plsEdgeBody, plsPin)
            else:
                raise Exception()
        elif descriptor["pins"]["rows"] == 2:
            if eq(descriptor["pins"]["pitch"], 2.0):
                pld2Body = lookup(templates, "PatPLD2Body").parent
                pld2EdgeBody = lookup(templates, "PatPLD2EdgeBody").parent
                pld2Pin = lookup(templates, "PatPLD2Pin").parent

                referenceObject = (pld2Body, pld2EdgeBody, pld2Pin)
            elif eq(descriptor["pins"]["pitch"], 2.54):
                pldBody = lookup(templates, "PatPLDBody").parent
                pldEdgeBody = lookup(templates, "PatPLDEdgeBody").parent
                pldPin = lookup(templates, "PatPLDPin").parent

                referenceObject = (pldBody, pldEdgeBody, pldPin)
            else:
                raise Exception()
        else:
            raise Exception()

        return PinHeader.buildHeaderBody(
                referenceObject[0], referenceObject[1], referenceObject[2],
                (descriptor["pins"]["columns"], descriptor["pins"]["rows"]),
                metricToImperial(descriptor["pins"]["pitch"]),
                descriptor["title"])


class BoxHeader:
    @staticmethod
    def buildHeaderBody(modelBody, modelPin, count, length, pitch, name):
        DEFAULT_WIDTH = metricToImperial(20.34)
        delta = (length - DEFAULT_WIDTH) / 2.

        leftPart, rightPart = model.Transform(), model.Transform()
        leftPart.translate([-delta, 0., 0.])
        rightPart.translate([delta, 0., 0.])
        transforms = [model.Transform(), leftPart, rightPart]
        body = copy.deepcopy(modelBody)
        body.applyTransforms(transforms)
        body.translate([delta, pitch / 2., 0.001])
        body.appearance().normals = debugNormals
        body.appearance().smooth = debugSmoothShading

        pins = []
        for i in range(0, count[0]):
            pin = model.Mesh(parent=modelPin, name="%s_%uPin%u" % (name, count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, pitch / 2., 0.001])
            pin.appearance().normals = debugNormals
            pin.appearance().smooth = debugSmoothShading
            pins.append(pin)

        return [body] + pins

    @staticmethod
    def build(materials, templates, descriptor):
        def eq(a, b):
            TOLERANCE = 0.001
            return a - TOLERANCE <= b <= a + TOLERANCE

        if descriptor["pins"]["rows"] != 2:
            raise Exception()
        if not eq(descriptor["pins"]["pitch"], 2.54):
            raise Exception()

        bhBody = lookup(templates, "PatBHBody").parent
        bhPin = lookup(templates, "PatBHPin").parent

        #Modified BH models
        regions = [
                (((0.7, 3.0, 4.0), (-2.5, -3.0, -0.5)), 1),
                (((6.5, 3.0, 4.0), ( 4.5, -3.0, -0.5)), 2)]
        bhAttributedBody = model.AttributedMesh(name="PatBHAttributed", regions=regions)
        bhAttributedBody.append(bhBody)
        bhAttributedBody.visualAppearance = bhBody.appearance()

        return BoxHeader.buildHeaderBody(
                bhAttributedBody, bhPin,
                (descriptor["pins"]["columns"], descriptor["pins"]["rows"]),
                metricToImperial(descriptor["body"]["length"]),
                metricToImperial(descriptor["pins"]["pitch"]),
                descriptor["title"])


types = [PinHeader, BoxHeader]
