#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# primitives.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import curves
from wrlconv import model

def limitVectorPair(a, b):
    ab = a + b
    aProjAB, bProjAB = reverseProjection(a, ab), reverseProjection(b, ab)
    abPart = aProjAB if numpy.linalg.norm(aProjAB) > numpy.linalg.norm(bProjAB) else bProjAB
    scale = numpy.linalg.norm(abPart) / numpy.linalg.norm(ab)
    return a * scale, b * scale

def hmils(values):
    # Convert millimeters to hundreds of mils
    try:
        return numpy.array([v / 2.54 for v in values])
    except TypeError:
        return values / 2.54

def projection(a, b):
    # Return projection of a vector a in the direction of a vector b
    bn = model.normalize(b)
    return numpy.dot(a, bn) * bn

def reorderPoints(e, n):
    return [e[1], e[0]] if e[0] != n else e

def reverseProjection(a, b):
    an = model.normalize(a)
    bn = model.normalize(b)
    dot = numpy.dot(an, bn)

    if dot != 0.0:
        return (numpy.linalg.norm(a) / dot) * bn
    else:
        # Two segments lie on a same line
        raise Exception()

def calcBezierWeight(a=None, b=None, angle=None):
    if angle is None:
        if a is None or b is None:
            # User must provide vectors a and b when angle argument is not used
            raise Exception()
        angle = model.angle(a, b)

    return (4.0 / 3.0) * math.tan(angle / 4.0)

def sortEdgePoints(e):
    return (min(e), max(e))

def defaultQuadFaceFunctor(p, resolution=(1, 1), inversion=False):
    return curves.BezierQuad(
            (
                    p[1],
                    p[1] + (p[0] - p[1]) / 3.0,
                    p[0] + (p[1] - p[0]) / 3.0,
                    p[0]
            ), (
                    p[1] + (p[2] - p[1]) / 3.0,
                    p[1] + (p[2] - p[1]) / 3.0 + (p[0] - p[1]) / 3.0,
                    p[0] + (p[3] - p[0]) / 3.0 + (p[1] - p[0]) / 3.0,
                    p[0] + (p[3] - p[0]) / 3.0
            ), (
                    p[2] + (p[1] - p[2]) / 3.0,
                    p[2] + (p[1] - p[2]) / 3.0 + (p[3] - p[2]) / 3.0,
                    p[3] + (p[0] - p[3]) / 3.0 + (p[2] - p[3]) / 3.0,
                    p[3] + (p[0] - p[3]) / 3.0
            ), (
                    p[2],
                    p[2] + (p[3] - p[2]) / 3.0,
                    p[3] + (p[2] - p[3]) / 3.0,
                    p[3]
            ), resolution, inversion)

def defaultTriFaceFunctor(p, resolution=1, inversion=False):
    return curves.BezierTriangle(
            (
                    p[0],
                    p[0] + (p[2] - p[0]) / 3.0,
                    p[0] + (p[1] - p[0]) / 3.0
            ), (
                    p[2],
                    p[2] + (p[1] - p[2]) / 3.0,
                    p[2] + (p[0] - p[2]) / 3.0
            ), (
                    p[1],
                    p[1] + (p[0] - p[1]) / 3.0,
                    p[1] + (p[2] - p[1]) / 3.0
            ),
            (p[0] + p[1] + p[2]) / 3.0,
            resolution, inversion)


class JointEdge:
    def __init__(self, num, vec, mNum, mVec, nNum, nVec, chamfer, normalized=True):
        self.num = num
        self.mNum = mNum
        self.nNum = nNum
        self.normals = {}

        mNorm = mVec - projection(mVec, vec)
        nNorm = nVec - projection(nVec, vec)
        length = chamfer / math.sqrt(2.0 * (1.0 - math.cos(model.angle(mNorm, nNorm))))

        if normalized:
            self.normals[self.mNum] = model.normalize(mNorm) * length
            self.normals[self.nNum] = model.normalize(nNorm) * length
        else:
            self.normals[self.mNum] = model.normalize(mVec) * length
            self.normals[self.nNum] = model.normalize(nVec) * length
        self.roundness = calcBezierWeight(mNorm, nNorm)

        self.m = self.normals[self.mNum]
        self.n = self.normals[self.nNum]

    def equalize(self, other):
        m = (self.m + other.m) / 2.0
        n = (self.n + other.n) / 2.0
        self.normals[self.mNum] = other.normals[other.mNum] = m
        self.normals[self.nNum] = other.normals[other.nNum] = n
        self.m = other.m = m
        self.n = other.n = n

    def shrink(self, other):
        a, b = self.normals[other.num], other.normals[self.num]
        a, b = limitVectorPair(a, b)

        self.normals[other.num] = a
        other.normals[self.num] = b

        if other.num == self.mNum:
            self.m = a
        else:
            self.n = a

        if self.num == other.mNum:
            other.m = b
        else:
            other.n = b


class TriJoint:
    def __init__(self, vertices, num, uNum, vNum, wNum, chamfer):
        self.num = num
        self.pos = vertices[self.num]

        uVec = vertices[uNum] - self.pos
        vVec = vertices[vNum] - self.pos
        wVec = vertices[wNum] - self.pos

        self.u = JointEdge(uNum, uVec, wNum, wVec, vNum, vVec, chamfer)
        self.v = JointEdge(vNum, vVec, wNum, wVec, uNum, uVec, chamfer)
        self.w = JointEdge(wNum, wVec, vNum, vVec, uNum, uVec, chamfer)

        self.u.shrink(self.v)
        self.u.shrink(self.w)
        self.v.shrink(self.w)

        self.edges = {}
        self.edges[self.u.num] = self.u
        self.edges[self.v.num] = self.v
        self.edges[self.w.num] = self.w

    def face(self, keys):
        return self.pos + self.edges[keys[0]].normals[keys[1]] + self.edges[keys[1]].normals[keys[0]]

    def mesh(self, resolution, inversion=False):
        uv = self.u.n + self.v.n
        uw = self.u.m + self.w.n
        vw = self.v.m + self.w.m
        uRoundness = self.u.roundness
        vRoundness = self.v.roundness
        wRoundness = self.w.roundness
        inversion = inversion ^ (numpy.linalg.det(numpy.matrix([uv, uw, vw])) < 0.0)

        return curves.BezierTriangle(
                (
                        self.pos + uv,
                        self.pos + uv - self.u.n * uRoundness,
                        self.pos + uv - self.v.n * vRoundness
                ), (
                        self.pos + uw,
                        self.pos + uw - self.w.n * wRoundness,
                        self.pos + uw - self.u.m * uRoundness
                ), (
                        self.pos + vw,
                        self.pos + vw - self.v.m * vRoundness,
                        self.pos + vw - self.w.m * wRoundness
                ),
                self.pos + (uv + uw + vw) * 0.114,
                resolution, inversion)

    def nearest(self, p0, p1, constraints=[]):
        pairs = [(self.u.num, self.v.num), (self.u.num, self.w.num), (self.v.num, self.w.num)]

        for constraint in constraints:
            for pair in pairs:
                if constraint not in pair:
                    pairs.remove(pair)
                    break

        rawNormal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face(pair) for pair in pairs]
        normals = [numpy.cross(p0 - x, p1 - x) for x in positions]
        angles = [model.angle(rawNormal, x) for x in normals]
        return pairs[angles.index(min(angles))]


class QuadJoint:
    class Diag:
        def __init__(self, u, v):
            self.u = u
            self.v = v


    def __init__(self, vertices, num, neighbors, chamfer, sharpness):
        self.num = num
        self.pos = vertices[self.num]

        vecs = {i: vertices[i] - self.pos for i in neighbors}
        mean = sum(vecs.values())
        initvec = vecs[neighbors[0]]
        dirs = [(neighbors[0], 0.0)]
        for v in neighbors[1:]:
            vec = vecs[v] - projection(vecs[v], mean)
            angle = model.angle(initvec, vec)
            if numpy.linalg.det(numpy.matrix([initvec, vec, mean])) < 0.0:
                angle = -angle
            dirs.append((v, angle))
        dirs = sorted(dirs, key=lambda x: x[1])
        sections = ((dirs[0][0], dirs[2][0]), (dirs[1][0], dirs[3][0]))
        angles = (
                model.angle(vecs[sections[0][0]], vecs[sections[0][1]]),
                model.angle(vecs[sections[1][0]], vecs[sections[1][1]]))

        self.flat0 = angles[0] > sharpness
        self.flat1 = angles[1] > sharpness
        self.roundness0 = calcBezierWeight(angle=abs(angles[0]))
        self.roundness1 = calcBezierWeight(angle=abs(angles[1]))

        if self.flat0:
            self.diag0 = QuadJoint.Diag(
                    JointEdge(
                            sections[1][0], vecs[sections[1][0]],
                            sections[0][0], numpy.zeros(3),
                            sections[0][1], numpy.zeros(3),
                            chamfer),
                    JointEdge(
                            sections[1][1], vecs[sections[1][1]],
                            sections[0][0], numpy.zeros(3),
                            sections[0][1], numpy.zeros(3),
                            chamfer))
        else:
            self.diag0 = QuadJoint.Diag(
                    JointEdge(
                            sections[1][0], vecs[sections[1][0]],
                            sections[0][0], vecs[sections[0][0]],
                            sections[0][1], vecs[sections[0][1]],
                            chamfer, not self.flat1),
                    JointEdge(
                            sections[1][1], vecs[sections[1][1]],
                            sections[0][0], vecs[sections[0][0]],
                            sections[0][1], vecs[sections[0][1]],
                            chamfer, not self.flat1))

        if self.flat1:
            self.diag1 = QuadJoint.Diag(
                    JointEdge(
                            sections[0][0], vecs[sections[0][0]],
                            sections[1][0], numpy.zeros(3),
                            sections[1][1], numpy.zeros(3),
                            chamfer),
                    JointEdge(
                            sections[0][1], vecs[sections[0][1]],
                            sections[1][0], numpy.zeros(3),
                            sections[1][1], numpy.zeros(3),
                            chamfer))
        else:
            self.diag1 = QuadJoint.Diag(
                    JointEdge(
                            sections[0][0], vecs[sections[0][0]],
                            sections[1][0], vecs[sections[1][0]],
                            sections[1][1], vecs[sections[1][1]],
                            chamfer, not self.flat0),
                    JointEdge(
                            sections[0][1], vecs[sections[0][1]],
                            sections[1][0], vecs[sections[1][0]],
                            sections[1][1], vecs[sections[1][1]],
                            chamfer, not self.flat0))

        if self.flat0:
            self.diag1.u.equalize(self.diag1.v)
        if self.flat1:
            self.diag0.u.equalize(self.diag0.v)

        # self.diag0.u.shrink(self.diag1.u)
        # self.diag0.u.shrink(self.diag1.v)
        # self.diag0.v.shrink(self.diag1.u)
        # self.diag0.v.shrink(self.diag1.v)

        self.edges = {}
        self.edges[sections[1][0]] = self.diag0.u
        self.edges[sections[1][1]] = self.diag0.v
        self.edges[sections[0][0]] = self.diag1.u
        self.edges[sections[0][1]] = self.diag1.v

    def face(self, keys):
        return self.pos + self.edges[keys[0]].normals[keys[1]] + self.edges[keys[1]].normals[keys[0]]

    def mesh(self, resolution, inversion=False):
        if self.flat0 or self.flat1:
            return None

        corners = [
                self.diag0.u.m + self.diag1.u.m,
                self.diag0.u.n + self.diag1.v.m,
                self.diag0.v.n + self.diag1.v.n,
                self.diag0.v.m + self.diag1.u.n]
        inversion = inversion ^ (numpy.linalg.det(numpy.matrix([*corners[0:3]])) < 0.0)

        return curves.BezierQuad(
                (
                        self.pos + corners[0],
                        self.pos + corners[0] - self.diag0.u.m * self.roundness0,
                        self.pos + corners[1] - self.diag0.u.n * self.roundness0,
                        self.pos + corners[1]
                ), (
                        self.pos + corners[0] - self.diag1.u.m * self.roundness1,
                        self.pos + corners[0] - self.diag1.u.m * self.roundness1 - self.diag0.u.m * self.roundness0,
                        self.pos + corners[1] - self.diag1.v.m * self.roundness1 - self.diag0.u.n * self.roundness0,
                        self.pos + corners[1] - self.diag1.v.m * self.roundness1
                ), (
                        self.pos + corners[3] - self.diag1.u.n * self.roundness1,
                        self.pos + corners[3] - self.diag1.u.n * self.roundness1 - self.diag0.v.m * self.roundness0,
                        self.pos + corners[2] - self.diag1.v.n * self.roundness1 - self.diag0.v.n * self.roundness0,
                        self.pos + corners[2] - self.diag1.v.n * self.roundness1
                ), (
                        self.pos + corners[3],
                        self.pos + corners[3] - self.diag0.v.m * self.roundness0,
                        self.pos + corners[2] - self.diag0.v.n * self.roundness0,
                        self.pos + corners[2]
                ), resolution, inversion)

    def nearest(self, p0, p1, constraints=[]):
        pairs = [
                (self.diag0.u.num, self.diag1.u.num),
                (self.diag0.u.num, self.diag1.v.num),
                (self.diag0.v.num, self.diag1.v.num),
                (self.diag0.v.num, self.diag1.u.num)]

        for constraint in constraints:
            for pair in pairs:
                if constraint not in pair:
                    pairs.remove(pair)
                    break

        rawNormal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face(pair) for pair in pairs]
        normals = [numpy.cross(p0 - x, p1 - x) for x in positions]
        angles = [model.angle(rawNormal, x) for x in normals]
        return pairs[angles.index(min(angles))]


def makeBodyCap(corners, radius, offset, edges):
    if edges % 4 != 0:
        raise Exception()
    if len(corners) != 4:
        raise Exception()

    mesh = model.Mesh()
    zMean = sum([corner[2] for corner in corners]) / float(len(corners))

    angle, delta = 0, math.pi * 2.0 / edges
    for i in range(0, edges):
        x, y = radius * math.cos(angle) + offset[0], radius * math.sin(angle) + offset[1]
        mesh.geoVertices.append(numpy.array([x, y, zMean]))
        angle += delta

    for corner in corners:
        mesh.geoVertices.append(corner)

    sectors = int(edges / 4)
    for i in range(0, 4):
        for j in range(0, sectors):
            mesh.geoPolygons.append([sectors * i + j, edges + i, (sectors * i + j + 1) % edges])
        mesh.geoPolygons.append([edges + i, sectors * i, edges + (i - 1) % 4])

    return mesh

def makeBodyMark(radius, edges):
    mesh = model.Mesh()

    angle, delta = 0, math.pi * 2.0 / edges
    for i in range(0, edges):
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        mesh.geoVertices.append(numpy.array([x, y, 0.0]))
        angle += delta
    [mesh.geoPolygons.append([0, i, i + 1]) for i in range(1, edges - 1)]

    return mesh

def makeRoundedEdge(beg, end, resolution, inversion=False):
    edges = list(beg.edges[end.num].normals.keys())
    begPosM = beg.pos + beg.edges[edges[0]].normals[end.num]
    begPosN = beg.pos + beg.edges[edges[1]].normals[end.num]
    begDirM = beg.edges[end.num].normals[edges[0]]
    begDirN = beg.edges[end.num].normals[edges[1]]

    edges = list(end.edges[beg.num].normals.keys())
    endPosM = end.pos + end.edges[edges[0]].normals[beg.num]
    endPosN = end.pos + end.edges[edges[1]].normals[beg.num]
    endDirM = end.edges[beg.num].normals[edges[0]]
    endDirN = end.edges[beg.num].normals[edges[1]]

    if model.Mesh.isclose(begDirM, begDirN) and model.Mesh.isclose(endDirM, endDirN):
        return None

    begRoundness = beg.edges[end.num].roundness
    endRoundness = end.edges[beg.num].roundness
    dir = ((endPosM + endPosN) / 2.0 - (begPosM + begPosN) / 2.0) / 3.0

    if numpy.linalg.det(numpy.matrix([begDirM, begDirN, dir])) < 0.0:
        begDirM, begDirN = begDirN, begDirM
        begPosM, begPosN = begPosN, begPosM
    if numpy.linalg.det(numpy.matrix([endDirM, endDirN, dir])) < 0.0:
        endDirM, endDirN = endDirN, endDirM
        endPosM, endPosN = endPosN, endPosM

    # TODO Interpolate start, end in middle points along dir
    return curves.BezierQuad(
            (
                    begPosM + begDirM,
                    begPosM + begDirM * (1.0 - begRoundness),
                    begPosN + begDirN * (1.0 - begRoundness),
                    begPosN + begDirN
            ), (
                    begPosM + dir + begDirM,
                    begPosM + dir + begDirM * (1.0 - begRoundness),
                    begPosN + dir + begDirN * (1.0 - begRoundness),
                    begPosN + dir + begDirN
            ), (
                    endPosM - dir + endDirM,
                    endPosM - dir + endDirM * (1.0 - endRoundness),
                    endPosN - dir + endDirN * (1.0 - endRoundness),
                    endPosN - dir + endDirN
            ), (
                    endPosM + endDirM,
                    endPosM + endDirM * (1.0 - endRoundness),
                    endPosN + endDirN * (1.0 - endRoundness),
                    endPosN + endDirN
            ), resolution, inversion)

def roundModelEdges(vertices, edges, faces, chamfer, sharpness, edgeResolution, lineResolution):
    meshes = []
    tesselatedEdges = []
    processedEdges = []
    vertexCounters = {}

    for entry in edges:
        [tesselatedEdges.append((entry[i], entry[i + 1])) for i in range(0, len(entry) - 1)]

    for e in tesselatedEdges:
        for v in e:
            if v in vertexCounters:
                vertexCounters[v] += 1
            else:
                vertexCounters[v] = 1

    joints = {}

    # Make intersections of three edges
    triJointIndices = filter(lambda x: vertexCounters[x] == 3, vertexCounters)

    for v in triJointIndices:
        neighbors = []
        [neighbors.append(reorderPoints(e, v)[1]) for e in tesselatedEdges if v in e]
        joints[v] = TriJoint(vertices, v, *neighbors, chamfer)
        mesh = joints[v].mesh(edgeResolution)
        if mesh is not None:
            meshes.append(mesh)

    # Make intersections of four edges
    quadJointIndices = filter(lambda x: vertexCounters[x] == 4, vertexCounters)

    for v in quadJointIndices:
        neighbors = []
        [neighbors.append(reorderPoints(e, v)[1]) for e in tesselatedEdges if v in e]
        joints[v] = QuadJoint(vertices, v, neighbors, chamfer, sharpness)
        mesh = joints[v].mesh((edgeResolution, edgeResolution))
        if mesh is not None:
            meshes.append(mesh)

    for v in joints:
        for key in joints[v].edges:
            uname = sortEdgePoints((v, key))
            if uname not in processedEdges:
                processedEdges.append(uname)
            else:
                continue

            mesh = makeRoundedEdge(joints[v], joints[key], (lineResolution, edgeResolution))
            if mesh is not None:
                meshes.append(mesh)

    for entry in faces:
        try:
            indices, size = entry[0], len(entry[0])
            functor = entry[1]
        except:
            indices, size = entry, len(entry)
            functor = defaultQuadFaceFunctor if size == 4 else defaultTriFaceFunctor

        faceVertices = []
        for i in range(0, size):
            next, prev = indices[(i + 1) % size], indices[i - 1]
            joint = joints[indices[i]]
            constraints = []

            if next in joint.edges:
                constraints.append(next)
            if prev in joint.edges:
                constraints.append(prev)

            pos = joint.face(joint.nearest(vertices[prev], vertices[next], constraints))
            faceVertices.append(pos)
        meshes.append(functor(faceVertices))

    # Build resulting mesh
    mesh = model.Mesh()
    [mesh.append(m) for m in meshes]
    mesh.optimize()

    return mesh

def makeBox(size, chamfer, edgeResolution, lineResolution, band=None, bandWidth=0.0,
        markRadius=None, markOffset=numpy.array([0.0, 0.0]), markResolution=24):
    x, y, z = numpy.array(size) / 2.0
    if band is not None:
        dr = bandWidth * math.sqrt(0.5)
    else:
        dr = 0.0

    if markRadius is not None:
        topFaceFunc = lambda vertices: makeBodyCap(vertices, markRadius, markOffset, markResolution)
    else:
        topFaceFunc = defaultQuadFaceFunctor

    vs = [
            numpy.array([ x,  y, z]),
            numpy.array([-x,  y, z]),
            numpy.array([-x, -y, z]),
            numpy.array([ x, -y, z]),

            numpy.array([ x + dr,  y + dr, band]),
            numpy.array([-x - dr,  y + dr, band]),
            numpy.array([-x - dr, -y - dr, band]),
            numpy.array([ x + dr, -y - dr, band]),

            numpy.array([ x,  y, -z]),
            numpy.array([-x,  y, -z]),
            numpy.array([-x, -y, -z]),
            numpy.array([ x, -y, -z])]
    es = [
            # Top
            [0, 1, 2, 3, 0],
            # Middle
            [4, 5, 6, 7, 4],
            # Bottom
            [8, 9, 10, 11, 8],
            # Sides, upper half
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7],
            # Sides, lower half
            [4, 8],
            [5, 9],
            [6, 10],
            [7, 11]
    ]
    fs = [
            # Top
            ([0, 1, 2, 3], topFaceFunc),
            # Bottom
            [11, 10, 9, 8],
            # Sides, upper half
            [4, 5, 1, 0],
            [5, 6, 2, 1],
            [6, 7, 3, 2],
            [7, 4, 0, 3],
            # Sides, lower half
            [8, 9, 5, 4],
            [9, 10, 6, 5],
            [10, 11, 7, 6],
            [11, 8, 4, 7]]

    body = roundModelEdges(vertices=vs, edges=es, faces=fs, chamfer=chamfer, sharpness=math.pi * (5.0 / 6.0),
            edgeResolution=edgeResolution, lineResolution=lineResolution)

    if markRadius is not None:
        mark = makeBodyMark(markRadius, markResolution)
        mark.translate(numpy.array([*markOffset, z]))
        mark.apply()
    else:
        mark = None
    return (body, mark)

def makeRoundedBox(size, roundness, chamfer, edgeResolution, lineResolution, band=None, bandWidth=0.0,
        markRadius=None, markOffset=numpy.array([0.0, 0.0]), markResolution=24):
    x, y, z = numpy.array(size) / 2.0
    r = roundness * math.sqrt(0.5)

    if band is not None:
        dr = bandWidth * math.sqrt(0.5)
    else:
        raise Exception() # TODO

    if markRadius is not None:
        topFaceFunc = lambda vertices: makeBodyCap(vertices, markRadius, markOffset, markResolution)
    else:
        topFaceFunc = defaultQuadFaceFunctor

    vs = [
            numpy.array([     x,  y - r, z]),
            numpy.array([ x - r,      y, z]),
            numpy.array([-x + r,      y, z]),
            numpy.array([    -x,  y - r, z]),
            numpy.array([    -x, -y + r, z]),
            numpy.array([-x + r,     -y, z]),
            numpy.array([ x - r,     -y, z]),
            numpy.array([     x, -y + r, z]),

            numpy.array([     x + dr,  y - r + dr, band]),
            numpy.array([ x - r + dr,      y + dr, band]),
            numpy.array([-x + r - dr,      y + dr, band]),
            numpy.array([    -x - dr,  y - r + dr, band]),
            numpy.array([    -x - dr, -y + r - dr, band]),
            numpy.array([-x + r - dr,     -y - dr, band]),
            numpy.array([ x - r + dr,     -y - dr, band]),
            numpy.array([     x + dr, -y + r - dr, band]),

            numpy.array([     x,  y - r, -z]),
            numpy.array([ x - r,      y, -z]),
            numpy.array([-x + r,      y, -z]),
            numpy.array([    -x,  y - r, -z]),
            numpy.array([    -x, -y + r, -z]),
            numpy.array([-x + r,     -y, -z]),
            numpy.array([ x - r,     -y, -z]),
            numpy.array([     x, -y + r, -z])]
    es = [
            # Top
            [0, 1, 2, 3, 4, 5, 6, 7, 0],
            # Middle
            [8, 9, 10, 11, 12, 13, 14, 15, 8],
            # Bottom
            [16, 17, 18, 19, 20, 21, 22, 23, 16],
            # Sides, upper half
            [0, 8],
            [1, 9],
            [2, 10],
            [3, 11],
            [4, 12],
            [5, 13],
            [6, 14],
            [7, 15],
            # Sides, lower half
            [8, 16],
            [9, 17],
            [10, 18],
            [11, 19],
            [12, 20],
            [13, 21],
            [14, 22],
            [15, 23]
    ]
    fs = [
            # Top
            [0, 1, 2, 3],
            ([0, 3, 4, 7], topFaceFunc),
            [7, 4, 5, 6],
            # Bottom
            [19, 18, 17, 16],
            [23, 20, 19, 16],
            [22, 21, 20, 23],
            # Sides, upper half
            [8, 9, 1, 0],
            [9, 10, 2, 1],
            [10, 11, 3, 2],
            [11, 12, 4, 3],
            [12, 13, 5, 4],
            [13, 14, 6, 5],
            [14, 15, 7, 6],
            [15, 8, 0, 7],
            # Sides, lower half
            [16, 17, 9, 8],
            [17, 18, 10, 9],
            [18, 19, 11, 10],
            [19, 20, 12, 11],
            [20, 21, 13, 12],
            [21, 22, 14, 13],
            [22, 23, 15, 14],
            [23, 16, 8, 15]]

    body = roundModelEdges(vertices=vs, edges=es, faces=fs, chamfer=chamfer, sharpness=math.pi * (5.0 / 6.0),
            edgeResolution=edgeResolution, lineResolution=lineResolution)

    if markRadius is not None:
        mark = makeBodyMark(markRadius, markResolution)
        mark.translate(numpy.array([*markOffset, z]))
        mark.apply()
    else:
        mark = None
    return (body, mark)

def makeSlopedBox(size, chamfer, slope, slopeHeight, edgeResolution, lineResolution, band=None, bandWidth=0.0):
    x, y, z = numpy.array(size) / 2.0
    mz = z - slopeHeight
    sy = y - slopeHeight / math.tan(slope)

    if band is not None:
        dr = bandWidth * math.sqrt(0.5)
    else:
        raise Exception() # TODO

    offset = dr - mz * (dr / z)
    mx = x + offset
    my = y + offset

    vs = [
            numpy.array([ x,  y, -z]),
            numpy.array([-x,  y, -z]),
            numpy.array([-x, -y, -z]),
            numpy.array([ x, -y, -z]),

            numpy.array([ x + dr,  y + dr, band]),
            numpy.array([-x - dr,  y + dr, band]),
            numpy.array([-x - dr, -y - dr, band]),
            numpy.array([ x + dr, -y - dr, band]),

            numpy.array([ mx, my, mz]),
            numpy.array([-mx, my, mz]),

            numpy.array([ x, sy, z]),
            numpy.array([-x, sy, z]),
            numpy.array([-x, -y, z]),
            numpy.array([ x, -y, z])
    ]
    es = [
            [0, 1, 2, 3, 0],
            [4, 5, 6, 7, 4],
            [8, 9],
            [10, 11, 12, 13, 10],
            [3, 7, 13], [10, 8, 4, 0],
            [2, 6, 12], [11, 9, 5, 1]
    ]
    fs = [
            [3, 2, 1, 0],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
            [4, 5, 9, 8],
            [8, 9, 11, 10],
            [6, 7, 13, 12],
            [10, 11, 12, 13],
            [5, 6, 9],
            [12, 11, 9, 6],
            [8, 7, 4],
            [7, 8, 10, 13]
    ]

    return roundModelEdges(vertices=vs, edges=es, faces=fs, chamfer=chamfer, sharpness=math.pi * (5.0 / 6.0),
            edgeResolution=edgeResolution, lineResolution=lineResolution)

def makeRoundedRect(size, roundness, segments):
    dx, dy = size[0] / 2.0, size[1] / 2.0
    r = roundness
    rb = roundness * calcBezierWeight(angle=math.pi / 2.0)

    shape = []
    shape.append(curves.Line((-dx + r, dy, 0.0), (dx - r, dy, 0.0), 1))
    shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0), (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
    shape.append(curves.Line((dx, dy - r, 0.0), (dx, -dy + r, 0.0), 1))
    shape.append(curves.Bezier((dx, -dy + r, 0.0), (0.0, -rb, 0.0), (dx - r, -dy, 0.0), (rb, 0.0, 0.0), segments))
    shape.append(curves.Line((dx - r, -dy, 0.0), (-dx + r, -dy, 0.0), 1))
    shape.append(curves.Bezier((-dx + r, -dy, 0.0), (-rb, 0.0, 0.0), (-dx, -dy + r, 0.0), (0.0, -rb, 0.0), segments))
    shape.append(curves.Line((-dx, -dy + r, 0.0), (-dx, dy - r, 0.0), 1))
    shape.append(curves.Bezier((-dx, dy - r, 0.0), (0.0, rb, 0.0), (-dx + r, dy, 0.0), (-rb, 0.0, 0.0), segments))

    return shape

def makePinCurve(pinShapeSize, pinHeight, pinLength, pinSlope, chamfer, roundness,
        pivot=0.5, outerRadiusK=0.35, innerRadiusK=0.3, chamferResolution=2, edgeResolution=3):
    curve = []

    rLimit = min(pinHeight, pinLength)
    r1 = outerRadiusK * rLimit
    r2 = innerRadiusK * rLimit
    xMean = pinLength * pivot
    yMean = pinHeight / 2.0

    a1 = yMean - pinShapeSize[1] / 2.0 - r1 * (1.0 - math.sin(pinSlope))
    a2 = yMean - r2 * (1.0 - math.sin(pinSlope))

    y0 = pinShapeSize[1] / 2.0
    y1 = y0
    y2 = y1
    y3 = yMean - a1
    y4 = yMean + a2
    y5 = pinHeight
    y6 = y5

    x0 = pinLength
    x1 = pinLength - chamfer
    x2 = pinLength * pivot + a1 * math.tan(pinSlope) + r1 * math.cos(pinSlope)
    x3 = pinLength * pivot + a1 * math.tan(pinSlope)
    x4 = pinLength * pivot - a2 * math.tan(pinSlope)
    x5 = pinLength * pivot - a2 * math.tan(pinSlope) - r2 * math.cos(pinSlope)
    x6 = 0.0

    p0 = numpy.array([x0, 0.0, y0])
    p1 = numpy.array([x1, 0.0, y1])
    p2 = numpy.array([x2, 0.0, y2])
    p3 = numpy.array([x3, 0.0, y3])
    p4 = numpy.array([x4, 0.0, y4])
    p5 = numpy.array([x5, 0.0, y5])
    p6 = numpy.array([x6, 0.0, y6])

    # Control points of segment 0
    p0t1 = (p1 - p0) / 3.0
    p1t0 = (p0 - p1) / 3.0

    # Control points of segment 3
    lp2p3 = math.sin((math.pi / 2.0 - pinSlope) / 2.0) * numpy.linalg.norm(p2 - p3)
    p2t3 = numpy.array([-lp2p3, 0.0, 0.0]) * roundness
    p3t2 = lp2p3 * model.normalize(p3 - p4) * roundness

    # Control points of segment 5
    lp4p5 = math.sin((math.pi / 2.0 - pinSlope) / 2.0) * numpy.linalg.norm(p4 - p5)
    p4t5 = lp4p5 * model.normalize(p4 - p3) * roundness
    p5t4 = numpy.array([lp4p5, 0.0, 0.0]) * roundness

    curve.append(curves.Bezier(p0, p0t1, p1, p1t0, chamferResolution))
    curve.append(curves.Line(p1, p2, 1))
    curve.append(curves.Bezier(p2, p2t3, p3, p3t2, edgeResolution))
    curve.append(curves.Line(p3, p4, 1))
    curve.append(curves.Bezier(p4, p4t5, p5, p5t4, edgeResolution))
    curve.append(curves.Line(p5, p6, 1))

    return curve

def buildLoftMesh(slices, fillStart=True, fillEnd=True):
    mesh = model.Mesh()

    number = len(slices[0])
    [mesh.geoVertices.extend(points) for points in slices]

    if fillStart:
        vIndex = len(mesh.geoVertices)
        mesh.geoVertices.append(calcMedianPoint(slices[0]))
        [mesh.geoPolygons.append([i, i + 1, vIndex]) for i in range(0, number - 1)]

    for i in range(0, len(slices) - 1):
        for j in range(0, number - 1):
            mesh.geoPolygons.append([
                    i * number + j,
                    (i + 1) * number + j,
                    (i + 1) * number + j + 1,
                    i * number + j + 1])

    if fillEnd:
        vIndex = len(mesh.geoVertices)
        mesh.geoVertices.append(calcMedianPoint(slices[-1]))
        [mesh.geoPolygons.append([i, i + 1, vIndex]) for i in range((len(slices) - 1) * number, len(slices) * number)]

    return mesh

def calcMedianPoint(vertices):
    if len(vertices) == 0:
        raise Exception()

    maxPos = minPos = vertices[0]
    for v in vertices:
        maxPos = numpy.maximum(maxPos, v)
        minPos = numpy.minimum(minPos, v)
    return (maxPos + minPos) / 2.0

def makePinMesh(pinShapeSize, pinHeight, pinLength, pinSlope, endSlope, chamferResolution, edgeResolution):
    chamfer = min(pinShapeSize) / 10.0
    curveRoundness = calcBezierWeight(angle=math.pi / 2.0 + pinSlope)

    shape = makeRoundedRect(size=pinShapeSize, roundness=chamfer, segments=chamferResolution)
    shapePoints = []
    [shapePoints.extend(element.tesselate()) for element in shape]
    shapePoints = curves.optimize(shapePoints)

    path = makePinCurve(pinShapeSize=pinShapeSize, pinHeight=pinHeight, pinLength=pinLength, pinSlope=pinSlope,
            chamfer=chamfer, roundness=curveRoundness, pivot=0.45,
            chamferResolution=chamferResolution, edgeResolution=edgeResolution)
    pathPoints = []
    [pathPoints.extend(element.tesselate()) for element in path]
    pathPoints = curves.optimize(pathPoints)

    def meshRotationFunc(t):
        current = int(t * (len(pathPoints) - 1))
        if current == len(pathPoints) - 1:
            return numpy.array([endSlope, 0.0, 0.0])
        else:
            return numpy.zeros(3)

    def meshScalingFunc(t):
        if chamferResolution >= 1:
            current = int(t * (len(pathPoints) - 1))

            if current < chamferResolution:
                size = numpy.array(pinShapeSize)
                scale = (size - chamfer * 2.0) / size
                tSeg = math.sin((math.pi / 2.0) * (current / chamferResolution))
                tScale = scale + (numpy.array([1.0, 1.0]) - scale) * tSeg
                return numpy.array([*tScale, 1.0])
            else:
                return numpy.ones(3)
        else:
            return numpy.ones(3)

    slices = curves.loft(path=pathPoints, shape=shapePoints, rotation=meshRotationFunc, scaling=meshScalingFunc)
    return buildLoftMesh(slices, True, False)
