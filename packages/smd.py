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
    LINE_RESOLUTION = 1
    SEAM_RESOLUTION = 3


    class PinDesc:
        def __init__(self, pattern, offsetFunctor=None, descriptor=None):
            if pattern is None and descriptor is None:
                # Not enough information
                raise Exception()

            if pattern is not None:
                self.length = pattern.length
                self.offset = pattern.offset
                self.shape = pattern.shape

            if descriptor is not None:
                if 'length' in descriptor:
                    self.length = primitives.hmils(descriptor['length'])
                if 'shape' in descriptor:
                    self.shape = primitives.hmils(descriptor['shape'])
                    self.offset = offsetFunctor(self.shape)

        def __hash__(self):
            return hash((self.length, *self.shape))

        @classmethod
        def makePattern(cls, offsetFunctor, descriptor):
            if offsetFunctor is None or descriptor is None:
                raise Exception()

            return cls(None, offsetFunctor, descriptor)


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
                seamResolution=SOT.SEAM_RESOLUTION,
                lineResolution=SOT.LINE_RESOLUTION,
                band=bandOffset,
                bandWidth=SOT.BAND_WIDTH,
                markRadius=markRadius,
                markOffset=markOffset,
                markResolution=SOT.SEAM_RESOLUTION * 8)

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
        bodySlope = 2.0 * bandWidthProj / bodySize[2]
        pinOffsetFunctor = lambda shape: numpy.array([0.0, bandWidthProj - bodySlope * shape[1] / 2.0])
        pinHeight = bodySize[2] / 2.0 + SOT.BODY_OFFSET_Z + bandOffset

        try:
            pinPattern = SOT.PinDesc.makePattern(pinOffsetFunctor, descriptor['pins']['default'])
        except KeyError:
            pinPattern = None

        pinEntries = {}
        for i in range(1, descriptor['pins']['count'] + 1):
            key = str(i)
            try:
                if descriptor['pins'][key] is not None:
                    pinEntries[i] = SOT.PinDesc(pinPattern, pinOffsetFunctor, descriptor['pins'][key])
            except KeyError:
                pinEntries[i] = SOT.PinDesc(pinPattern)
        pinGroups = set(pinEntries.values())
        pinGroupMeshes = {}

        for group in pinGroups:
            mesh = primitives.makePinMesh(
                    pinShapeSize=group.shape,
                    pinHeight=pinHeight,
                    pinLength=group.length,
                    pinSlope=pinSlope,
                    endSlope=math.atan(bodySlope),
                    chamferSegments=SOT.CHAMFER_RESOLUTION,
                    slopeSegments=SOT.SEAM_RESOLUTION)

            if 'Pin' in materials:
                mesh.appearance().material = materials['Pin']

            pinGroupMeshes[hash(group)] = mesh

        return self.generatePinRows(
                count=descriptor['pins']['count'],
                size=bodySize,
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
            position = numpy.array([x, y])

            if i + columns in entries:
                entry = entries[i + columns]
                mesh = patterns[hash(entry)]
                meshes.append(makePin(mesh, position + entry.offset, math.pi, i + columns))

            if i in entries:
                entry = entries[i]
                mesh = patterns[hash(entry)]
                meshes.append(makePin(mesh, -position + entry.offset * [1, -1], 0.0, i))

        return meshes

    def generate(self, materials, templates, descriptor):
        return self.generateBody(materials, descriptor) + self.generatePins(materials, descriptor)


types = [
        Chip,
        SOT
]
