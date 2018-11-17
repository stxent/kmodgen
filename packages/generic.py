#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# generic.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import re

def lookup(meshList, meshName):
    found = []
    for entry in meshList:
        if re.search('^{:s}'.format(meshName), entry.ident, re.S) is not None:
            found.append(entry)
    return found


class GenericModelFilter:
    PIVOT_NONE, PIVOT_MEDIAN_CENTER, PIVOT_BOUNDING_BOX_CENTER = 0, 1, 2

    def __init__(self, alignment=PIVOT_NONE):
        self.alignment = alignment

    def generate(self, materials, templates, descriptor):
        meshes = lookup(templates, descriptor['title'])

        if len(meshes) > 0 and self.alignment != GenericModelFilter.PIVOT_NONE:
            if self.alignment == GenericModelFilter.PIVOT_MEDIAN_CENTER:
                # Find median point of the group of objects
                pivot = numpy.zeros(3)
                for mesh in meshes:
                    pivot += mesh.transform.matrix.getA()[:,3][0:3]
                pivot *= numpy.array([1.0 / len(meshes), 1.0 / len(meshes), 0.0])
            elif self.alignment == GenericModelFilter.PIVOT_BOUNDING_BOX_CENTER:
                # Find bounding box center
                coordMin, coordMax = None, None

                for mesh in meshes:
                    column = mesh.transform.matrix.getA()[:,3][0:3]
                    if coordMin is None:
                        coordMin = coordMax = column
                    else:
                        coordMin = numpy.minimum(coordMin, column)
                        coordMax = numpy.maximum(coordMax, column)

                pivot = coordMin + (coordMax - coordMin) * numpy.array([0.5, 0.5, 0.0])

            # Move all objects in horizontal plane to the center of the scene
            for mesh in meshes:
                mesh.transform.translate(-pivot)

        return meshes


types = []
