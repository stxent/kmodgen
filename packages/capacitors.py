#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# capacitors.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import curves
from wrlconv import model


class RadialCapacitor:
    @staticmethod
    def buildBumpedCap(slices, beginning, sections, sectionWidth, capRadius, bodyRadius):
        if sections < 2:
            raise Exception()

        rot = lambda a, b: a if a < b else a - b if a >= 0 else b - a

        if beginning:
            vertices = [slices[i][0] for i in range(0, len(slices))]
        else:
            vertices = [slices[i][len(slices[i]) - 1] for i in range(0, len(slices))]
        center = sum(vertices) / len(slices)

        geoVertices = []
        geoPolygons = []

        depth = sectionWidth / 4.0
        firstCircleRadius = sectionWidth / 4.0 / math.sin(2.0 * math.pi / float(2 * sections))
        secondCircleRadius = sectionWidth / 2.0 / math.sin(2.0 * math.pi / float(2 * sections))
        firstCirclePoints, secondCirclePoints = [], []
        outerPoints = []
        bodyPoints = []
        for i in range(0, sections):
            angle = 2.0 * math.pi / float(sections) * float(i)
            vector = numpy.array([math.cos(angle), math.sin(angle), 0.0])
            firstCirclePoints.append(center + vector * firstCircleRadius + numpy.array([0.0, 0.0, -depth]))
            secondCirclePoints.append(center + vector * secondCircleRadius)

            angle = 2.0 * math.pi / float(sections) * (float(i) + 0.5)
            vector = numpy.array([math.cos(angle), math.sin(angle), 0.0])
            normal = numpy.array([math.cos(angle + math.pi / 2.0), math.sin(angle + math.pi / 2.0), 0.0])
            points = [
                    center + vector * capRadius + normal * sectionWidth / 2.0,
                    center + vector * capRadius + normal * sectionWidth / 4.0 + numpy.array([0.0, 0.0, -depth]),
                    center + vector * capRadius - normal * sectionWidth / 4.0 + numpy.array([0.0, 0.0, -depth]),
                    center + vector * capRadius - normal * sectionWidth / 2.0
            ]
            outerPoints.append(points)
            points = [
                    center + vector * bodyRadius + normal * sectionWidth / 2.0,
                    center + vector * bodyRadius + normal * sectionWidth / 4.0 + numpy.array([0.0, 0.0, -depth]),
                    center + vector * bodyRadius - normal * sectionWidth / 4.0 + numpy.array([0.0, 0.0, -depth]),
                    center + vector * bodyRadius - normal * sectionWidth / 2.0
            ]
            bodyPoints.append(points)

        edgePoints = []
        for i in range(0, sections):
            angle = lambda v: math.atan2((v - center)[1], (v - center)[0])
            belongs = lambda v, a, b: v >= a and v <= b if b >= a else v >= a or v <= b

            def comparator(a, b):
                aAngle, bAngle = angle(a), angle(b)
                return 0 if aAngle == bAngle else -1 if aAngle <= bAngle else 1

            innerRange = (outerPoints[rot(i - 1, sections)][0], outerPoints[i][3])
            outerRange = (outerPoints[rot(i - 1, sections)][3], outerPoints[i][0])
            inner = (angle(innerRange[0]), angle(innerRange[1]))
            outer = (angle(outerRange[0]), angle(outerRange[1]))

            normalAngles = (
                    2.0 * math.pi / float(sections) * (float(i) + 0.5) + math.pi / 2.0,
                    2.0 * math.pi / float(sections) * (float(i) - 0.5) + math.pi / 2.0
            )
            normals = (
                    numpy.array([math.cos(normalAngles[0]), math.sin(normalAngles[0]), 0.0]),
                    numpy.array([math.cos(normalAngles[1]), math.sin(normalAngles[1]), 0.0])
            )

            points = [v for v in vertices if belongs(angle(v), inner[0], inner[1])]

            for j in range(0, len(vertices)):
                seg = (vertices[rot(j - 1, len(vertices))], vertices[j])

                if not belongs(angle(seg[0]), outer[0], outer[1]) and not belongs(angle(seg[1]), outer[0], outer[1]):
                    continue

                intersection = model.intersectLinePlane(secondCirclePoints[i], normals[0], seg[0], seg[1])
                if intersection is not None:
                    outerPoints[i][3] = intersection
                    points.append(intersection)

                intersection = model.intersectLinePlane(secondCirclePoints[i], normals[1], seg[0], seg[1])
                if intersection is not None:
                    outerPoints[rot(i - 1, sections)][0] = intersection
                    points.append(intersection)

            if inner[1] >= inner[0]:
                points = sorted(points, comparator)
            else:
                points = sorted(filter(lambda x: angle(x) >= 0.0, points), comparator)\
                        + sorted(filter(lambda x: angle(x) < 0.0, points), comparator)
            edgePoints.append(points)

        fcp = lambda a: rot(a, sections)
        geoVertices.extend(firstCirclePoints)
        scp = lambda a: sections + rot(a, sections)
        geoVertices.extend(secondCirclePoints)
        op = lambda a, b: 2 * sections + rot(a, sections) * 4 + rot(b, 4)
        [geoVertices.extend(points) for points in outerPoints]
        bp = lambda a, b: 6 * sections + rot(a, sections) * 4 + rot(b, 4)
        [geoVertices.extend(points) for points in bodyPoints]

        [geoVertices.extend(points) for points in edgePoints]
        def edgeIndices(a):
            return [10 * sections + sum(map(len, edgePoints[0:a])) + i for i in range(0, len(edgePoints[a]))]

        # Central polygon
        geoPolygons.append([i for i in range(0, sections)])
        for i in range(0, sections):
            # Bumped polygons
            geoPolygons.append([fcp(i + 1), fcp(i), op(i, 2), op(i, 1)])
            # Ramp polygons
            geoPolygons.append([scp(i + 1), fcp(i + 1), op(i, 1), op(i, 0)])
            geoPolygons.append([fcp(i), scp(i), op(i, 3), op(i, 2)])
            # Arc polygons
            geoPolygons.append([scp(i)] + edgeIndices(i))
            # Partially visible polygons
            geoPolygons.append([op(i, 0), op(i, 1), bp(i, 1), bp(i, 0)])
            geoPolygons.append([op(i, 2), op(i, 3), bp(i, 3), bp(i, 2)])
            geoPolygons.append([op(i, 1), op(i, 2), bp(i, 2), bp(i, 1)])
            geoPolygons.append([bp(i, 0), bp(i, 1), bp(i, 2), bp(i, 3)])

        # Generate object
        mesh = model.Mesh()
        mesh.geoVertices = geoVertices
        [mesh.geoPolygons.extend(model.Mesh.tesselate(patch)) for patch in geoPolygons]
        mesh.optimize()

        return mesh

    @staticmethod
    def buildCapacitorCurve(radius, height, curvature, bandOffset, capRadius, capDepth, chamfer,
            edgeDetails=3, bandDetails=4):

        if capRadius is not None and capDepth is not None and chamfer is None:
            raise Exception()

        curve = []

        # Bottom cap
        if capRadius is not None:
            if capDepth is not None:
                curve.append(curves.Line((capRadius, 0.0, capDepth - chamfer), (capRadius, 0.0, chamfer), 1))
                curve.append(curves.Line((capRadius, 0.0, chamfer), (capRadius + chamfer, 0.0, 0.0), 1))
                curve.append(curves.Line((capRadius + chamfer, 0.0, 0.0), (radius - curvature, 0.0, 0.0), 1))
            else:
                curve.append(curves.Line((capRadius, 0.0, 0.0), (radius - curvature, 0.0, 0.0), 1))

        # Plastic
        curve.append(curves.Bezier((radius - curvature, 0.0, 0.0), (curvature / 2.0, 0.0, 0.0),
                (radius, 0.0, curvature), (0.0, 0.0, -curvature / 2.0), edgeDetails))
        curve.append(curves.Line((radius, 0.0, curvature), (radius, 0.0, bandOffset - curvature * 2.0), 1))
        curve.append(curves.Bezier((radius, 0.0, bandOffset - curvature * 2.0), (0.0, 0.0, curvature),
                (radius - curvature, 0.0, bandOffset), (0.0, 0.0, -curvature), bandDetails))
        curve.append(curves.Bezier((radius - curvature, 0.0, bandOffset), (0.0, 0.0, curvature),
                (radius, 0.0, bandOffset + curvature * 2.0), (0.0, 0.0, -curvature), bandDetails))
        curve.append(curves.Line((radius, 0.0, bandOffset + curvature * 2.0), (radius, 0.0, height - curvature), 1))
        curve.append(curves.Bezier((radius, 0.0, height - curvature), (0.0, 0.0, curvature / 2.0),
                (radius - curvature, 0.0, height), (curvature / 2.0, 0.0, 0.0), edgeDetails))

        # Top cap
        if capRadius is not None:
            if capDepth is not None:
                curve.append(curves.Line((radius - curvature, 0.0, height), (capRadius + chamfer, 0.0, height), 1))
                curve.append(curves.Line((capRadius + chamfer, 0.0, height), (capRadius, 0.0, height - chamfer), 1))
                curve.append(curves.Line((capRadius, 0.0, height - chamfer), (capRadius, 0.0, height - capDepth), 1))
            else:
                curve.append(curves.Line((radius - curvature, 0.0, height), (capRadius, 0.0, height), 1))

        return curve

    @staticmethod
    def buildPinCurve(radius, height, curvature, edgeDetails=2):
        curve = []

        curve.append(curves.Bezier((radius - curvature, 0.0, -height), (curvature / 2.0, 0.0, 0.0),
                (radius, 0.0, -height + curvature), (0.0, 0.0, -curvature / 2.0), edgeDetails))
        curve.append(curves.Line((radius, 0.0, curvature - height), (radius, 0.0, 0.0), 1))

        return curve

    @staticmethod
    def buildCapacitorBody(curve, edges, polarized, materials, name, capSections, capInnerRadius, capOuterRadius,
            capSectionWidth, capBumpDepth):
        slices = curves.rotate(curve=curve, axis=(0.0, 0.0, 1.0), edges=edges)
        meshes = []

        bottomCap = curves.createTriCapMesh(slices, True)
        bottomCap.appearance().material = RadialCapacitor.mat(materials, 'Bottom')
        bottomCap.ident = name + 'BottomCap'
        meshes.append(bottomCap)

        if capSections == 1:
            topCap = curves.createTriCapMesh(slices, False)
        else:
            topCap = RadialCapacitor.buildBumpedCap(slices=slices, beginning=False, sections=capSections,
                    sectionWidth=capSectionWidth, capRadius=capInnerRadius, bodyRadius=capOuterRadius)
        topCap.appearance().material = RadialCapacitor.mat(materials, 'Top')
        topCap.ident = name + 'TopCap'
        meshes.append(topCap)

        if polarized:
            body = curves.createRotationMesh(slices[1:], False)
            body.appearance().material = RadialCapacitor.mat(materials, 'Body')
            body.ident = name + 'Body'
            meshes.append(body)

            mark = curves.createRotationMesh([slices[-1]] + slices[0:2], False)
            mark.appearance().material = RadialCapacitor.mat(materials, 'Mark')
            mark.ident = name + 'Mark'
            meshes.append(mark)
        else:
            body = curves.createRotationMesh(slices, True)
            body.appearance().material = RadialCapacitor.mat(materials, 'Body')
            body.ident = name + 'Body'
            meshes.append(body)

        return meshes

    @staticmethod
    def buildCapacitorPin(curve, edges):
        slices = curves.rotate(curve=curve, axis=(0.0, 0.0, 1.0), edges=edges)

        pin = curves.createRotationMesh(slices, True)
        pin.append(curves.createTriCapMesh(slices, True))
        pin.optimize()

        return pin

    @staticmethod
    def demangle(title):
        return title.replace('C-', 'Cap').replace('CP-', 'Cap').replace('R-', 'Radial').replace('A-', 'Axial')

    @staticmethod
    def mat(materials, name):
        if name in materials.keys():
            return materials[name]
        else:
            result = model.Material()
            result.color.ident = name
            return result

    @staticmethod
    def build(materials, templates, descriptor):
        title = RadialCapacitor.demangle(descriptor['title'])

        bodyDetails = descriptor['body']['details'] if 'details' in descriptor['body'].keys() else 3
        bodyEdges = descriptor['body']['edges'] if 'edges' in descriptor['body'].keys() else 24
        capSections = descriptor['caps']['sections'] if 'sections' in descriptor['caps'].keys() else 1

        meshes = []
        bodyCurve = RadialCapacitor.buildCapacitorCurve(
                model.metricToImperial(descriptor['body']['diameter']) / 2.0,
                model.metricToImperial(descriptor['body']['height']),
                model.metricToImperial(descriptor['body']['curvature']),
                model.metricToImperial(descriptor['body']['band']),
                model.metricToImperial(descriptor['caps']['diameter']) / 2.0,
                model.metricToImperial(descriptor['caps']['depth']),
                model.metricToImperial(descriptor['caps']['chamfer']),
                bodyDetails,
                bodyDetails + 1)

        bodyMesh = RadialCapacitor.buildCapacitorBody(
                bodyCurve,
                bodyEdges,
                descriptor['body']['stripe'],
                materials,
                title,
                capSections,
                model.metricToImperial(descriptor['caps']['diameter']) / 2.0,
                model.metricToImperial(descriptor['caps']['diameter'] + descriptor['body']['curvature']) / 2.0,
                model.metricToImperial(descriptor['body']['curvature']),
                model.metricToImperial(descriptor['body']['curvature']) / 2.0)
        meshes.extend(bodyMesh)

        pinCurve = RadialCapacitor.buildPinCurve(
                model.metricToImperial(descriptor['pins']['diameter']) / 2.0,
                model.metricToImperial(descriptor['pins']['height']),
                model.metricToImperial(descriptor['pins']['curvature']))

        pinMesh = RadialCapacitor.buildCapacitorPin(pinCurve, descriptor['pins']['edges'])
        pinMesh.appearance().material = RadialCapacitor.mat(materials, 'Pin')
        pinMesh.ident = title + 'Pin'

        spacing = model.metricToImperial(descriptor['pins']['spacing']) / 2.0
        posPin = model.Mesh(parent=pinMesh, name=pinMesh.ident + 'Pos')
        posPin.translate([-spacing, 0.0, 0.0])
        meshes.append(posPin)
        negPin = model.Mesh(parent=pinMesh, name=pinMesh.ident + 'Neg')
        negPin.translate([spacing, 0.0, 0.0])
        meshes.append(negPin)

        return meshes


types = [RadialCapacitor]
