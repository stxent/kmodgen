#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# capacitors.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from wrlconv import curves
from wrlconv import model

debugNormals = False
debugSmoothShading = False

def buildCapacitorCurve(radius, height, curvature, bandOffset, capRadius, capDepth, chamfer=None,
        edgeDetails=3, bandDetails=4):
    if capRadius is not None and capDepth is not None and chamfer is None:
        raise Exception()

    curve = []

    #Bottom cap
    if capRadius is not None:
        if capDepth is not None:
            curve.append(curves.Line((capRadius, 0., capDepth - chamfer), (capRadius, 0., chamfer), 1))
            curve.append(curves.Line((capRadius, 0., chamfer), (capRadius + chamfer, 0., 0.), 1))
            curve.append(curves.Line((capRadius + chamfer, 0., 0.), (radius - curvature, 0., 0.), 1))
        else:
            curve.append(curves.Line((capRadius, 0., 0.), (radius - curvature, 0., 0.), 1))

    #Plastic
    curve.append(curves.Bezier((radius - curvature, 0., 0.), (curvature / 2., 0., 0.),
            (radius, 0., curvature), (0., 0., -curvature / 2.), edgeDetails))
    curve.append(curves.Line((radius, 0., curvature), (radius, 0., bandOffset - curvature * 2.), 1))
    curve.append(curves.Bezier((radius, 0., bandOffset - curvature * 2.), (0., 0., curvature),
            (radius - curvature, 0., bandOffset), (0., 0., -curvature), bandDetails))
    curve.append(curves.Bezier((radius - curvature, 0., bandOffset), (0., 0., curvature),
            (radius, 0., bandOffset + curvature * 2.), (0., 0., -curvature), bandDetails))
    curve.append(curves.Line((radius, 0., bandOffset + curvature * 2.), (radius, 0., height - curvature), 1))
    curve.append(curves.Bezier((radius, 0., height - curvature), (0., 0., curvature / 2.),
            (radius - curvature, 0., height), (curvature / 2., 0., 0.), edgeDetails))

    #Top cap
    if capRadius is not None:
        if capDepth is not None:
            curve.append(curves.Line((radius - curvature, 0., height), (capRadius + chamfer, 0., height), 1))
            curve.append(curves.Line((capRadius + chamfer, 0., height), (capRadius, 0., height - chamfer), 1))
            curve.append(curves.Line((capRadius, 0., height - chamfer), (capRadius, 0., height - capDepth), 1))
        else:
            curve.append(curves.Line((radius - curvature, 0., height), (capRadius, 0., height), 1))

    return curve

def buildPinCurve(radius, height, curvature, edgeDetails=2):
    curve = []

    curve.append(curves.Bezier((radius - curvature, 0., -height), (curvature / 2., 0., 0.),
            (radius, 0., -height + curvature), (0., 0., -curvature / 2.), edgeDetails))
    curve.append(curves.Line((radius, 0., curvature - height), (radius, 0., 0.), 1))

    return curve

def buildCapacitorBody(curve, edges, polarized, materials, name):
    slices = curves.rotate(curve, (0., 0., 1.), edges)
    meshes = []

    bottomCap = curves.createTriCapMesh(slices, True)
    bottomCap.appearance().material = materials["Bottom"]
    bottomCap.appearance().normals = debugNormals
    bottomCap.appearance().smooth = debugSmoothShading
    bottomCap.ident = name + "BottomCap"
    meshes.append(bottomCap)

    topCap = curves.createTriCapMesh(slices, False)
    topCap.appearance().material = materials["Top"]
    topCap.appearance().normals = debugNormals
    topCap.appearance().smooth = debugSmoothShading
    topCap.ident = name + "TopCap"
    meshes.append(topCap)

    if polarized:
        body = curves.createRotationMesh(slices[1:], False)
        body.appearance().material = materials["Body"]
        body.appearance().normals = debugNormals
        body.appearance().smooth = debugSmoothShading
        body.ident = name + "Body"
        meshes.append(body)

        mark = curves.createRotationMesh([slices[-1]] + slices[0:2], False)
        mark.appearance().material = materials["Mark"]
        mark.appearance().normals = debugNormals
        mark.appearance().smooth = debugSmoothShading
        mark.ident = name + "Mark"
        meshes.append(mark)
    else:
        body = curves.createRotationMesh(slices, True)
        body.appearance().material = materials["Body"]
        body.appearance().normals = debugNormals
        body.appearance().smooth = debugSmoothShading
        body.ident = name + "Body"
        meshes.append(body)

    return meshes

def buildCapacitorPin(curve, edges):
    slices = curves.rotate(curve, (0., 0., 1.), edges)

    pin = curves.createRotationMesh(slices, True)
    pin.append(curves.createTriCapMesh(slices, True))
    pin.optimize()

    pin.appearance().normals = debugNormals
    pin.appearance().smooth = debugSmoothShading

    return pin

def demangle(title):
    return title.replace("C-", "Cap").replace("CP-", "Cap").replace("R-", "Radial").replace("A-", "Axial")

def metricToImperial(value):
    return value / 2.54 #Convert millimeters to hundreds of mils


class RadialCapacitor:
    @staticmethod
    def build(materials, patterns, descriptor):
        for matGroup in ["Body", "Mark", "Top", "Bottom", "Pin"]:
            if matGroup not in materials.keys():
                materials[matGroup] = model.Material()
                materials[matGroup].color.ident = matGroup
    
        title = demangle(descriptor["title"])
    
        meshes = []
        bodyCurve = buildCapacitorCurve(
                metricToImperial(descriptor["body"]["radius"]),
                metricToImperial(descriptor["body"]["height"]),
                metricToImperial(descriptor["body"]["curvature"]),
                metricToImperial(descriptor["body"]["band"]),
                metricToImperial(descriptor["caps"]["radius"]),
                metricToImperial(descriptor["caps"]["depth"]),
                metricToImperial(descriptor["caps"]["chamfer"]))
        meshes.extend(buildCapacitorBody(bodyCurve, descriptor["body"]["edges"], descriptor["body"]["stripe"],
                materials, title))
    
        pinCurve = buildPinCurve(
                metricToImperial(descriptor["pins"]["radius"]),
                metricToImperial(descriptor["pins"]["height"]),
                metricToImperial(descriptor["pins"]["curvature"]))
    
        pinMesh = buildCapacitorPin(pinCurve, descriptor["pins"]["edges"])
        pinMesh.appearance().material = materials["Pin"]
        pinMesh.ident = title + "Pin"
    
        spacing = metricToImperial(descriptor["pins"]["spacing"]) / 2.
        posPin = model.Mesh(parent=pinMesh, name=pinMesh.ident + "Pos")
        posPin.translate([-spacing, 0., 0.])
        meshes.append(posPin)
        negPin = model.Mesh(parent=pinMesh, name=pinMesh.ident + "Neg")
        negPin.translate([spacing, 0., 0.])
        meshes.append(negPin)
    
        return meshes


types = [RadialCapacitor]
