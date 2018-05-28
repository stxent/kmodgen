#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2015 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import re

from wrlconv import model

def eq(a, b):
    TOLERANCE = 0.001
    return a - TOLERANCE <= b <= a + TOLERANCE

def lookup(meshList, meshName):
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            return entry
    raise Exception()


class PinHeader:
    def __init__(self):
        pass

    def generateHeaderBody(self, materials, modelBody, modelEdge, modelPin, bodyTransform, count, pitch, name):
        shift = pitch / 2.0 if count[1] > 1 else 0.0

        body = model.Mesh(name='{:s}_{:d}Body'.format(name, count[0] * count[1]))
        body.visualAppearance = modelBody.appearance()

        pins = []
        for i in range(0, count[0]):
            if i == 0:
                segment = copy.deepcopy(modelEdge)
                segment.rotate([0.0, 0.0, 1.0], math.pi)
            elif i == count[0] - 1:
                segment = copy.deepcopy(modelEdge)
                segment.rotate([0.0, 0.0, 1.0], 0.0)
            else:
                segment = copy.deepcopy(modelBody)
            segment.translate([float(i) * pitch, shift, 0.0])
            body.append(segment)

            pin = model.Mesh(parent=modelPin, name='{:s}_{:d}Pin{:d}'.format(name, count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, shift, 0.001])
            if 'Pin' in materials.keys():
                pin.appearance().material = materials['Pin']
            pins.append(pin)

        body.transform = copy.deepcopy(bodyTransform)
        body.translate([0.0, 0.0, 0.001])
        body.optimize()
        if 'Body' in materials.keys():
            body.appearance().material = materials['Body']

        return [body] + pins

    def generate(self, materials, templates, descriptor):
        transform = model.Transform()
        pitch200 = eq(descriptor['pins']['pitch'], 2.0)
        pitch254 = eq(descriptor['pins']['pitch'], 2.54)

        if not pitch200 and not pitch254:
            raise Exception()

        if descriptor['pins']['rows'] == 1:
            if pitch200:
                objectNames = ['PatPLS2Body', 'PatPLS2EdgeBody', 'PatPLS2Pin']
            elif pitch254:
                objectNames = ['PatPLSBody', 'PatPLSEdgeBody', 'PatPLSPin']
        elif descriptor['pins']['rows'] == 2:
            if pitch200:
                objectNames = ['PatPLD2Body', 'PatPLD2EdgeBody', 'PatPLD2Pin']
            elif pitch254:
                objectNames = ['PatPLDBody', 'PatPLDEdgeBody', 'PatPLDPin']
        else:
            raise Exception()

        referenceObject = [lookup(templates, name).parent for name in objectNames]

        return self.generateHeaderBody(
                materials,
                referenceObject[0], referenceObject[1], referenceObject[2], transform,
                (descriptor['pins']['columns'], descriptor['pins']['rows']),
                model.metricToImperial(descriptor['pins']['pitch']),
                descriptor['title'])


class Jumper(PinHeader):
    def __init__(self):
        PinHeader.__init__(self)

    def generate(self, materials, templates, descriptor):
        objects = PinHeader.generate(self, materials, templates, descriptor)

        pitch200 = eq(descriptor['pins']['pitch'], 2.0)
        pitch254 = eq(descriptor['pins']['pitch'], 2.54)

        if pitch200:
            body = lookup(templates, 'PatPLS2Jumper').parent
        elif pitch254:
            body = lookup(templates, 'PatPLSJumper').parent
        else:
            raise Exception()

        return objects + [body]


class RightAnglePinHeader(PinHeader):
    def __init__(self):
        PinHeader.__init__(self)

    def generate(self, materials, templates, descriptor):
        transform = model.Transform()
        pitch200 = eq(descriptor['pins']['pitch'], 2.0)
        pitch254 = eq(descriptor['pins']['pitch'], 2.54)

        if pitch200:
            transform.translate([0.0, -0.391, 0.3937])
            transform.rotate([1.0, 0.0, 0.0], math.pi / 2.0)
        elif pitch254:
            transform.translate([0.0, -0.557, 0.5])
            transform.rotate([1.0, 0.0, 0.0], math.pi / 2.0)
        else:
            raise Exception()

        if descriptor['pins']['rows'] == 1:
            if pitch200:
                objectNames = ['PatPLS2Body', 'PatPLS2EdgeBody', 'PatPLS2RPin']
            elif pitch254:
                objectNames = ['PatPLSBody', 'PatPLSEdgeBody', 'PatPLSRPin']
        elif descriptor['pins']['rows'] == 2:
            if pitch200:
                objectNames = ['PatPLD2Body', 'PatPLD2EdgeBody', 'PatPLD2RPin']
            elif pitch254:
                objectNames = ['PatPLDBody', 'PatPLDEdgeBody', 'PatPLDRPin']
        else:
            raise Exception()

        referenceObject = [lookup(templates, name).parent for name in objectNames]

        return self.generateHeaderBody(
                materials,
                referenceObject[0], referenceObject[1], referenceObject[2], transform,
                (descriptor['pins']['columns'], descriptor['pins']['rows']),
                model.metricToImperial(descriptor['pins']['pitch']),
                descriptor['title'])


class BoxHeader:
    def __init__(self):
        pass

    def generateHeaderBody(self, materials, modelBody, modelPin, count, length, pitch, name):
        DEFAULT_WIDTH = model.metricToImperial(20.34)
        delta = (length - DEFAULT_WIDTH) / 2.0

        leftPart, rightPart = model.Transform(), model.Transform()
        leftPart.translate([-delta, 0.0, 0.0])
        rightPart.translate([delta, 0.0, 0.0])
        transforms = [model.Transform(), leftPart, rightPart]
        body = copy.deepcopy(modelBody)
        body.applyTransforms(transforms)
        body.translate([delta, pitch / 2.0, 0.001])
        if 'Body' in materials.keys():
            body.appearance().material = materials['Body']

        pins = []
        for i in range(0, count[0]):
            pin = model.Mesh(parent=modelPin, name='{:s}_{:d}Pin{:d}'.format(name, count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, pitch / 2.0, 0.001])
            if 'Pin' in materials.keys():
                pin.appearance().material = materials['Pin']
            pins.append(pin)

        return [body] + pins

    def generate(self, materials, templates, descriptor):
        if descriptor['pins']['rows'] != 2:
            raise Exception()
        if not eq(descriptor['pins']['pitch'], 2.54):
            raise Exception()

        bhBody = lookup(templates, 'PatBHBody').parent
        bhPin = lookup(templates, 'PatBHPin').parent

        # Modified BH models
        regions = [
                (((0.7, 3.0, 4.0), (-2.5, -3.0, -0.5)), 1),
                (((6.5, 3.0, 4.0), ( 4.5, -3.0, -0.5)), 2)
        ]
        bhAttributedBody = model.AttributedMesh(name='PatBHAttributed', regions=regions)
        bhAttributedBody.append(bhBody)
        bhAttributedBody.visualAppearance = bhBody.appearance()

        return self.generateHeaderBody(
                materials,
                bhAttributedBody, bhPin,
                (descriptor['pins']['columns'], descriptor['pins']['rows']),
                model.metricToImperial(descriptor['body']['size'][0]),
                model.metricToImperial(descriptor['pins']['pitch']),
                descriptor['title'])


types = [PinHeader, RightAnglePinHeader, BoxHeader, Jumper]
