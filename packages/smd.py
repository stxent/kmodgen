#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import model
from packages import generic
import primitives

class Chip(generic.GenericModelFilter):
    def __init__(self):
        generic.GenericModelFilter.__init__(self, Chip.PIVOT_BOUNDING_BOX_CENTER)


class SOT:
    BODY_CHAMFER = primitives.hmils(0.05)
    BODY_OFFSET_Z = primitives.hmils(0.1)

    BAND_WIDTH = primitives.hmils(0.1)

    MARK_MARGIN = primitives.hmils(0.4)
    MARK_RADIUS = primitives.hmils(0.2)

    CHAMFER_RESOLUTION = 1
    LINE_RESOLUTION    = 1
    EDGE_RESOLUTION    = 3


    class PinDesc:
        def __init__(self, pattern, slope=None, descriptor=None):
            if pattern is None and descriptor is None:
                # Not enough information
                raise Exception()

            if pattern is not None:
                self.length = pattern.length
                self.planarOffset = pattern.planarOffset
                self.verticalOffset = pattern.verticalOffset
                self.shape = pattern.shape

            if descriptor is not None:
                if 'length' in descriptor:
                    self.length = primitives.hmils(descriptor['length'])
                if 'shape' in descriptor:
                    self.shape = primitives.hmils(descriptor['shape'])
                    self.planarOffset = -abs(self.shape[1] * math.sin(slope) / 2.0)
                    self.verticalOffset = self.shape[1] * math.cos(slope) / 2.0
                    if slope < 0:
                        self.verticalOffset = -self.verticalOffset
                self.length -= self.planarOffset

        def __hash__(self):
            return hash((self.length, *self.shape))

        @classmethod
        def makePattern(cls, slope, descriptor):
            if slope is None or descriptor is None:
                raise Exception()

            return cls(None, slope, descriptor)


    def __init__(self):
        pass

    def generateBody(self, materials, descriptor):
        try:
            bandOffset = primitives.hmils(descriptor['band']['offset'])
        except:
            bandOffset = 0.0

        try:
            markRadius = SOT.MARK_RADIUS if primitives.hmils(descriptor['mark']['dot']) else None
        except:
            markRadius = None

        bodySize = primitives.hmils(descriptor['body']['size'])
        markOffset = -(bodySize[0:2] / 2.0 - SOT.MARK_MARGIN)

        bodyMesh, markMesh = primitives.makeBox(
                size=bodySize,
                chamfer=SOT.BODY_CHAMFER,
                edgeResolution=SOT.EDGE_RESOLUTION,
                lineResolution=SOT.LINE_RESOLUTION,
                band=bandOffset,
                bandWidth=SOT.BAND_WIDTH,
                markRadius=markRadius,
                markOffset=markOffset,
                markResolution=SOT.EDGE_RESOLUTION * 8)

        bodyTransform = model.Transform()
        bodyTransform.translate([0.0, 0.0, bodySize[2] / 2.0 + SOT.BODY_OFFSET_Z])
        meshes = []

        if 'Body' in materials:
            bodyMesh.appearance().material = materials['Body']
        bodyMesh.apply(bodyTransform)
        bodyMesh.rename('Body')
        meshes.append(bodyMesh)

        if markMesh is not None:
            if 'Mark' in materials:
                markMesh.appearance().material = materials['Mark']
            markMesh.apply(bodyTransform)
            markMesh.rename('Mark')
            meshes.append(markMesh)

        return meshes

    def generatePins(self, materials, descriptor):
        try:
            pinSlope = descriptor['pins']['slope'] * math.pi / 180.0
        except:
            pinSlope = math.pi * (10.0 / 180.0)

        try:
            bandOffset = primitives.hmils(descriptor['band']['offset'])
        except:
            bandOffset = 0.0
        try:
            bandInversion = descriptor['band']['inverse']
        except:
            bandInversion = False

        bodySize = primitives.hmils(descriptor['body']['size'])
        bandWidthProj = SOT.BAND_WIDTH * math.sqrt(0.5)
        if bandInversion:
            bodySlope = -math.atan(bandWidthProj / (bodySize[2] / 2.0 + bandOffset))
        else:
            bodySlope = math.atan(bandWidthProj / (bodySize[2] / 2.0 - bandOffset))
        pinHeight = bodySize[2] / 2.0 + bandOffset + SOT.BODY_OFFSET_Z

        try:
            pinPattern = SOT.PinDesc.makePattern(bodySlope, descriptor['pins']['default'])
        except KeyError:
            pinPattern = None

        pinEntries = {}
        for i in range(1, descriptor['pins']['count'] + 1):
            key = str(i)
            try:
                if descriptor['pins'][key] is not None:
                    pinEntries[i] = SOT.PinDesc(pinPattern, bodySlope, descriptor['pins'][key])
            except KeyError:
                pinEntries[i] = SOT.PinDesc(pinPattern)
        pinGroups = set(pinEntries.values())
        pinGroupMeshes = {}

        for group in pinGroups:
            mesh = primitives.makePinMesh(
                    pinShapeSize=group.shape,
                    pinHeight=pinHeight + group.verticalOffset,
                    pinLength=group.length,
                    pinSlope=pinSlope,
                    endSlope=bodySlope,
                    chamferResolution=SOT.CHAMFER_RESOLUTION,
                    edgeResolution=SOT.EDGE_RESOLUTION)

            if 'Pin' in materials:
                mesh.appearance().material = materials['Pin']

            pinGroupMeshes[hash(group)] = mesh

        return self.generatePinRows(
                count=descriptor['pins']['count'],
                size=bodySize[0:2] + bandWidthProj * 2.0,
                pitch=primitives.hmils(descriptor['pins']['pitch']),
                patterns=pinGroupMeshes,
                entries=pinEntries)

    def generatePinRows(self, count, size, pitch, patterns, entries):
        def makePin(mesh, position, angle, number):
            pin = model.Mesh(parent=mesh, name='Pin{:d}'.format(number))
            pin.translate([*position, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        columns = int(count / 2)
        firstPinOffset = pitch * (columns - 1) / 2.0
        y = size[1] / 2.0

        meshes = []
        for i in range(1, columns + 1):
            x = pitch * (i - 1) - firstPinOffset

            if i + columns in entries:
                entry = entries[i + columns]
                mesh = patterns[hash(entry)]
                meshes.append(makePin(mesh, [x, y + entry.planarOffset], math.pi, i + columns))

            if i in entries:
                entry = entries[i]
                mesh = patterns[hash(entry)]
                meshes.append(makePin(mesh, [-x, -(y + entry.planarOffset)], 0.0, i))

        return meshes

    def generate(self, materials, templates, descriptor):
        return self.generateBody(materials, descriptor) + self.generatePins(materials, descriptor)


types = [
        Chip,
        SOT
]
