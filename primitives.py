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

def limit_vector_pair(a, b): # pylint: disable=invalid-name
    ab_sum = a + b
    a_proj_ab, b_proj_ab = reverse_projection(a, ab_sum), reverse_projection(b, ab_sum)
    if numpy.linalg.norm(a_proj_ab) > numpy.linalg.norm(b_proj_ab):
        ab_part = a_proj_ab
    else:
        ab_part = b_proj_ab
    scale = numpy.linalg.norm(ab_part) / numpy.linalg.norm(ab_sum)
    return a * scale, b * scale

def hmils(values):
    # Convert millimeters to hundreds of mils
    try:
        return numpy.array([value / 2.54 for value in values])
    except TypeError:
        return values / 2.54

def projection(a, b): # pylint: disable=invalid-name
    # Return projection of a vector a in the direction of a vector b
    b_norm = model.normalize(b)
    return numpy.dot(a, b_norm) * b_norm

def round1f(value):
    if int(value * 10) == int(value) * 10:
        return '{:d}'.format(int(value))
    return '{:.1f}'.format(value)

def round2f(value):
    if int(value * 100) == int(value * 10) * 10:
        return '{:.1f}'.format(value)
    return '{:.2f}'.format(value)

def reorder_points(e, n): # pylint: disable=invalid-name
    return [e[1], e[0]] if e[0] != n else e

def reverse_projection(a, b): # pylint: disable=invalid-name
    a_norm = model.normalize(a)
    b_norm = model.normalize(b)
    dot = numpy.dot(a_norm, b_norm)

    if dot == 0.0:
        # Two segments lie on a same line
        raise Exception()
    return (numpy.linalg.norm(a) / dot) * b_norm

def calc_bezier_weight(a=None, b=None, angle=None): # pylint: disable=invalid-name
    if angle is None:
        if a is None or b is None:
            # User must provide vectors a and b when angle argument is not used
            raise Exception()
        angle = model.angle(a, b)

    return (4.0 / 3.0) * math.tan(angle / 4.0)

def sort_edge_points(points):
    return (min(points), max(points))

def default_quad_face_functor(points, resolution=(1, 1), inversion=False):
    return curves.BezierQuad(
        (
            points[1],
            points[1] + (points[0] - points[1]) / 3.0,
            points[0] + (points[1] - points[0]) / 3.0,
            points[0]
        ), (
            points[1] + (points[2] - points[1]) / 3.0,
            points[1] + (points[2] - points[1]) / 3.0 + (points[0] - points[1]) / 3.0,
            points[0] + (points[3] - points[0]) / 3.0 + (points[1] - points[0]) / 3.0,
            points[0] + (points[3] - points[0]) / 3.0
        ), (
            points[2] + (points[1] - points[2]) / 3.0,
            points[2] + (points[1] - points[2]) / 3.0 + (points[3] - points[2]) / 3.0,
            points[3] + (points[0] - points[3]) / 3.0 + (points[2] - points[3]) / 3.0,
            points[3] + (points[0] - points[3]) / 3.0
        ), (
            points[2],
            points[2] + (points[3] - points[2]) / 3.0,
            points[3] + (points[2] - points[3]) / 3.0,
            points[3]
        ), resolution, inversion)

def default_tri_face_functor(points, resolution=1, inversion=False):
    return curves.BezierTriangle(
            (
                    points[0],
                    points[0] + (points[2] - points[0]) / 3.0,
                    points[0] + (points[1] - points[0]) / 3.0
            ), (
                    points[2],
                    points[2] + (points[1] - points[2]) / 3.0,
                    points[2] + (points[0] - points[2]) / 3.0
            ), (
                    points[1],
                    points[1] + (points[0] - points[1]) / 3.0,
                    points[1] + (points[2] - points[1]) / 3.0
            ),
            (points[0] + points[1] + points[2]) / 3.0,
            resolution, inversion)


class JointEdge:
    def __init__(self, num, vec, m_num, m_vec, n_num, n_vec, chamfer, normalized=True):
        self.num = num
        self.m_num = m_num
        self.n_num = n_num
        self.normals = {}

        m_norm = m_vec - projection(m_vec, vec)
        n_norm = n_vec - projection(n_vec, vec)
        length = chamfer / math.sqrt(2.0 * (1.0 - math.cos(model.angle(m_norm, n_norm))))

        if normalized:
            self.normals[self.m_num] = model.normalize(m_norm) * length
            self.normals[self.n_num] = model.normalize(n_norm) * length
        else:
            self.normals[self.m_num] = model.normalize(m_vec) * length
            self.normals[self.n_num] = model.normalize(n_vec) * length
        self.roundness = calc_bezier_weight(m_norm, n_norm)

        # pylint: disable=invalid-name
        self.m = self.normals[self.m_num]
        self.n = self.normals[self.n_num]
        # pylint: enable=invalid-name

    def equalize(self, other):
        # pylint: disable=invalid-name
        m = (self.m + other.m) / 2.0
        n = (self.n + other.n) / 2.0
        # pylint: enable=invalid-name

        self.normals[self.m_num] = other.normals[other.m_num] = m
        self.normals[self.n_num] = other.normals[other.n_num] = n
        self.m = other.m = m
        self.n = other.n = n

    def shrink(self, other):
        # pylint: disable=invalid-name
        a, b = self.normals[other.num], other.normals[self.num]
        a, b = limit_vector_pair(a, b)
        # pylint: enable=invalid-name

        self.normals[other.num] = a
        other.normals[self.num] = b

        if other.num == self.m_num:
            self.m = a
        else:
            self.n = a

        if self.num == other.m_num:
            other.m = b
        else:
            other.n = b


class TriJoint:
    def __init__(self, vertices, num, neighbors, chamfer):
        self.num = num
        self.pos = vertices[self.num]

        u_num, v_num, w_num = neighbors[0], neighbors[1], neighbors[2]

        u_vec = vertices[u_num] - self.pos
        v_vec = vertices[v_num] - self.pos
        w_vec = vertices[w_num] - self.pos

        # pylint: disable=invalid-name
        self.u = JointEdge(u_num, u_vec, w_num, w_vec, v_num, v_vec, chamfer)
        self.v = JointEdge(v_num, v_vec, w_num, w_vec, u_num, u_vec, chamfer)
        self.w = JointEdge(w_num, w_vec, v_num, v_vec, u_num, u_vec, chamfer)
        # pylint: enable=invalid-name

        self.u.shrink(self.v)
        self.u.shrink(self.w)
        self.v.shrink(self.w)

        self.edges = {}
        self.edges[self.u.num] = self.u
        self.edges[self.v.num] = self.v
        self.edges[self.w.num] = self.w

    def face(self, keys):
        return (self.pos
                + self.edges[keys[0]].normals[keys[1]]
                + self.edges[keys[1]].normals[keys[0]])

    def mesh(self, resolution, inversion=False):
        # pylint: disable=invalid-name
        uv = self.u.n + self.v.n
        uw = self.u.m + self.w.n
        vw = self.v.m + self.w.m
        # pylint: enable=invalid-name

        u_roundness = self.u.roundness
        v_roundness = self.v.roundness
        w_roundness = self.w.roundness
        inversion = inversion ^ (numpy.linalg.det(numpy.array([uv, uw, vw])) < 0.0)

        return curves.BezierTriangle(
            (
                self.pos + uv,
                self.pos + uv - self.u.n * u_roundness,
                self.pos + uv - self.v.n * v_roundness
            ), (
                self.pos + uw,
                self.pos + uw - self.w.n * w_roundness,
                self.pos + uw - self.u.m * u_roundness
            ), (
                self.pos + vw,
                self.pos + vw - self.v.m * v_roundness,
                self.pos + vw - self.w.m * w_roundness
            ),
            self.pos + (uv + uw + vw) * 0.114,
            resolution, inversion)

    def nearest(self, p0, p1, constraints=None): # pylint: disable=invalid-name
        pairs = [(self.u.num, self.v.num), (self.u.num, self.w.num), (self.v.num, self.w.num)]

        if constraints is not None:
            for constraint in constraints:
                for pair in pairs:
                    if constraint not in pair:
                        pairs.remove(pair)
                        break

        raw_normal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face(pair) for pair in pairs]
        normals = [numpy.cross(p0 - x, p1 - x) for x in positions]
        angles = [model.angle(raw_normal, x) for x in normals]
        return pairs[angles.index(min(angles))]


class QuadJoint:
    class Diag:
        def __init__(self, u, v): # pylint: disable=invalid-name
            # pylint: disable=invalid-name
            self.u = u
            self.v = v
            # pylint: enable=invalid-name


    def __init__(self, vertices, num, neighbors, chamfer, sharpness):
        self.num = num
        self.pos = vertices[self.num]

        vecs = {i: vertices[i] - self.pos for i in neighbors}
        mean = sum(vecs.values())
        initvec = vecs[neighbors[0]]
        dirs = [(neighbors[0], 0.0)]
        for vertex in neighbors[1:]:
            vec = vecs[vertex] - projection(vecs[vertex], mean)
            angle = model.angle(initvec, vec)
            if numpy.linalg.det(numpy.array([initvec, vec, mean])) < 0.0:
                angle = -angle
            dirs.append((vertex, angle))
        dirs = sorted(dirs, key=lambda x: x[1])
        sections = ((dirs[0][0], dirs[2][0]), (dirs[1][0], dirs[3][0]))
        angles = (model.angle(vecs[sections[0][0]], vecs[sections[0][1]]),
                  model.angle(vecs[sections[1][0]], vecs[sections[1][1]]))

        self.flat0 = angles[0] > sharpness
        self.flat1 = angles[1] > sharpness
        self.roundness0 = calc_bezier_weight(angle=abs(angles[0]))
        self.roundness1 = calc_bezier_weight(angle=abs(angles[1]))

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
        return (self.pos
                + self.edges[keys[0]].normals[keys[1]]
                + self.edges[keys[1]].normals[keys[0]])

    def mesh(self, resolution, inversion=False):
        if self.flat0 or self.flat1:
            return None

        corners = [self.diag0.u.m + self.diag1.u.m,
                   self.diag0.u.n + self.diag1.v.m,
                   self.diag0.v.n + self.diag1.v.n,
                   self.diag0.v.m + self.diag1.u.n]
        inversion = inversion ^ (numpy.linalg.det(numpy.array([*corners[0:3]])) < 0.0)

        return curves.BezierQuad(
            (
                self.pos + corners[0],
                self.pos + corners[0] - self.diag0.u.m * self.roundness0,
                self.pos + corners[1] - self.diag0.u.n * self.roundness0,
                self.pos + corners[1]
            ), (
                self.pos + corners[0] - self.diag1.u.m * self.roundness1,
                self.pos + corners[0]
                    - self.diag1.u.m * self.roundness1 - self.diag0.u.m * self.roundness0,
                self.pos + corners[1]
                    - self.diag1.v.m * self.roundness1 - self.diag0.u.n * self.roundness0,
                self.pos + corners[1] - self.diag1.v.m * self.roundness1
            ), (
                self.pos + corners[3] - self.diag1.u.n * self.roundness1,
                self.pos + corners[3]
                    - self.diag1.u.n * self.roundness1 - self.diag0.v.m * self.roundness0,
                self.pos + corners[2]
                    - self.diag1.v.n * self.roundness1 - self.diag0.v.n * self.roundness0,
                self.pos + corners[2] - self.diag1.v.n * self.roundness1
            ), (
                self.pos + corners[3],
                self.pos + corners[3] - self.diag0.v.m * self.roundness0,
                self.pos + corners[2] - self.diag0.v.n * self.roundness0,
                self.pos + corners[2]
            ), resolution, inversion)

    def nearest(self, p0, p1, constraints=None): # pylint: disable=invalid-name
        pairs = [(self.diag0.u.num, self.diag1.u.num),
                 (self.diag0.u.num, self.diag1.v.num),
                 (self.diag0.v.num, self.diag1.v.num),
                 (self.diag0.v.num, self.diag1.u.num)]

        if constraints is not None:
            for constraint in constraints:
                for pair in pairs:
                    if constraint not in pair:
                        pairs.remove(pair)
                        break

        raw_normal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face(pair) for pair in pairs]
        normals = [numpy.cross(p0 - x, p1 - x) for x in positions]
        angles = [model.angle(raw_normal, x) for x in normals]
        return pairs[angles.index(min(angles))]


def make_body_cap(corners, radius, offset, edges):
    if edges % 4 != 0:
        raise Exception()
    if len(corners) != 4:
        raise Exception()

    mesh = model.Mesh()
    z_mean = sum([corner[2] for corner in corners]) / float(len(corners))

    angle, delta = 0, math.pi * 2.0 / edges
    for i in range(0, edges):
        # pylint: disable=invalid-name
        x = radius * math.cos(angle) + offset[0]
        y = radius * math.sin(angle) + offset[1]
        # pylint: enable=invalid-name

        mesh.geo_vertices.append(numpy.array([x, y, z_mean]))
        angle += delta

    for corner in corners:
        mesh.geo_vertices.append(corner)

    sectors = int(edges / 4)
    for i in range(0, 4):
        for j in range(0, sectors):
            mesh.geo_polygons.append([sectors * i + j, edges + i, (sectors * i + j + 1) % edges])
        mesh.geo_polygons.append([edges + i, sectors * i, edges + (i - 1) % 4])

    return mesh

def make_body_mark(radius, edges):
    mesh = model.Mesh()

    angle, delta = 0, math.pi * 2.0 / edges
    for i in range(0, edges):
        x, y = radius * math.cos(angle), radius * math.sin(angle) # pylint: disable=invalid-name
        mesh.geo_vertices.append(numpy.array([x, y, 0.0]))
        angle += delta
    for i in range(1, edges - 1):
        mesh.geo_polygons.append([0, i, i + 1])

    return mesh

def make_rounded_edge(beg, end, resolution, inversion=False):
    edges = list(beg.edges[end.num].normals.keys())
    beg_pos_m = beg.pos + beg.edges[edges[0]].normals[end.num]
    beg_pos_n = beg.pos + beg.edges[edges[1]].normals[end.num]
    beg_dir_m = beg.edges[end.num].normals[edges[0]]
    beg_dir_n = beg.edges[end.num].normals[edges[1]]

    edges = list(end.edges[beg.num].normals.keys())
    end_pos_m = end.pos + end.edges[edges[0]].normals[beg.num]
    end_pos_n = end.pos + end.edges[edges[1]].normals[beg.num]
    end_dir_m = end.edges[beg.num].normals[edges[0]]
    end_dir_n = end.edges[beg.num].normals[edges[1]]

    if model.Mesh.isclose(beg_dir_m, beg_dir_n) and model.Mesh.isclose(end_dir_m, end_dir_n):
        return None

    beg_roundness = beg.edges[end.num].roundness
    end_roundness = end.edges[beg.num].roundness
    direction = ((end_pos_m + end_pos_n) / 2.0 - (beg_pos_m + beg_pos_n) / 2.0) / 3.0

    if numpy.linalg.det(numpy.array([beg_dir_m, beg_dir_n, direction])) < 0.0:
        beg_dir_m, beg_dir_n = beg_dir_n, beg_dir_m
        beg_pos_m, beg_pos_n = beg_pos_n, beg_pos_m
    if numpy.linalg.det(numpy.array([end_dir_m, end_dir_n, direction])) < 0.0:
        end_dir_m, end_dir_n = end_dir_n, end_dir_m
        end_pos_m, end_pos_n = end_pos_n, end_pos_m

    # TODO Interpolate start, end in middle points along direction
    return curves.BezierQuad(
        (
            beg_pos_m + beg_dir_m,
            beg_pos_m + beg_dir_m * (1.0 - beg_roundness),
            beg_pos_n + beg_dir_n * (1.0 - beg_roundness),
            beg_pos_n + beg_dir_n
        ), (
            beg_pos_m + direction + beg_dir_m,
            beg_pos_m + direction + beg_dir_m * (1.0 - beg_roundness),
            beg_pos_n + direction + beg_dir_n * (1.0 - beg_roundness),
            beg_pos_n + direction + beg_dir_n
        ), (
            end_pos_m - direction + end_dir_m,
            end_pos_m - direction + end_dir_m * (1.0 - end_roundness),
            end_pos_n - direction + end_dir_n * (1.0 - end_roundness),
            end_pos_n - direction + end_dir_n
        ), (
            end_pos_m + end_dir_m,
            end_pos_m + end_dir_m * (1.0 - end_roundness),
            end_pos_n + end_dir_n * (1.0 - end_roundness),
            end_pos_n + end_dir_n
        ), resolution, inversion)

def round_model_edges(vertices, edges, faces, chamfer, sharpness, edge_resolution, line_resolution):
    meshes = []
    tesselated_edges = []
    processed_edges = []
    vertex_counters = {}

    for entry in edges:
        for i in range(0, len(entry) - 1):
            tesselated_edges.append((entry[i], entry[i + 1]))

    for edge in tesselated_edges:
        for vertex in edge:
            if vertex in vertex_counters:
                vertex_counters[vertex] += 1
            else:
                vertex_counters[vertex] = 1

    joints = {}

    # Make intersections of three edges
    tri_joint_indices = filter(lambda x: vertex_counters[x] == 3, vertex_counters)

    for vertex in tri_joint_indices:
        neighbors = []
        for edge in tesselated_edges:
            if vertex in edge:
                neighbors.append(reorder_points(edge, vertex)[1])
        joints[vertex] = TriJoint(vertices, vertex, neighbors, chamfer)
        mesh = joints[vertex].mesh(edge_resolution)
        if mesh is not None:
            meshes.append(mesh)

    # Make intersections of four edges
    quad_joint_indices = filter(lambda x: vertex_counters[x] == 4, vertex_counters)

    for vertex in quad_joint_indices:
        neighbors = []
        for edge in tesselated_edges:
            if vertex in edge:
                neighbors.append(reorder_points(edge, vertex)[1])
        joints[vertex] = QuadJoint(vertices, vertex, neighbors, chamfer, sharpness)
        mesh = joints[vertex].mesh((edge_resolution, edge_resolution))
        if mesh is not None:
            meshes.append(mesh)

    for vertex in joints:
        for key in joints[vertex].edges:
            uname = sort_edge_points((vertex, key))
            if uname not in processed_edges:
                processed_edges.append(uname)
            else:
                continue

            mesh = make_rounded_edge(joints[vertex], joints[key],
                                     (line_resolution, edge_resolution))
            if mesh is not None:
                meshes.append(mesh)

    for entry in faces:
        try:
            indices, size = entry[0], len(entry[0])
            functor = entry[1]
        except TypeError:
            indices, size = entry, len(entry)
            functor = default_quad_face_functor if size == 4 else default_tri_face_functor

        face_vertices = []
        for i in range(0, size):
            next_edge, prev_edge = indices[(i + 1) % size], indices[i - 1]
            joint = joints[indices[i]]
            constraints = []

            if next_edge in joint.edges:
                constraints.append(next_edge)
            if prev_edge in joint.edges:
                constraints.append(prev_edge)

            pos = joint.face(joint.nearest(vertices[prev_edge], vertices[next_edge], constraints))
            face_vertices.append(pos)
        meshes.append(functor(face_vertices))

    # Build resulting mesh
    mesh = model.Mesh()
    for part in meshes:
        mesh.append(part)
    mesh.optimize()

    return mesh

def make_box(size, chamfer, edge_resolution, line_resolution, band=None, band_width=0.0,
             mark_radius=None, mark_offset=numpy.array([0.0, 0.0]), mark_resolution=24):
    x, y, z = numpy.array(size) / 2.0 # pylint: disable=invalid-name
    band_offset = band_width * math.sqrt(0.5) if band is not None else 0.0

    if mark_radius is not None:
        top_face_func = lambda vertices: make_body_cap(vertices, mark_radius, mark_offset,
            mark_resolution)
    else:
        top_face_func = default_quad_face_functor

    vertices = [
        numpy.array([ x,  y, z]),
        numpy.array([-x,  y, z]),
        numpy.array([-x, -y, z]),
        numpy.array([ x, -y, z]),

        numpy.array([ x + band_offset,  y + band_offset, band]),
        numpy.array([-x - band_offset,  y + band_offset, band]),
        numpy.array([-x - band_offset, -y - band_offset, band]),
        numpy.array([ x + band_offset, -y - band_offset, band]),

        numpy.array([ x,  y, -z]),
        numpy.array([-x,  y, -z]),
        numpy.array([-x, -y, -z]),
        numpy.array([ x, -y, -z])]
    edges = [
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
        [7, 11]]
    faces = [
        # Top
        ([0, 1, 2, 3], top_face_func),
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

    body = round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=line_resolution)

    if mark_radius is not None:
        mark = make_body_mark(mark_radius, mark_resolution)
        mark.translate(numpy.array([*mark_offset, z]))
        mark.apply()
    else:
        mark = None
    return (body, mark)

def make_rounded_box(size, roundness, chamfer, edge_resolution, line_resolution, band=None,
                     band_width=0.0, mark_radius=None, mark_offset=numpy.array([0.0, 0.0]),
                     mark_resolution=24):
    if band is None:
        raise Exception() # TODO

    # pylint: disable=invalid-name
    x, y, z = numpy.array(size) / 2.0
    r = roundness * math.sqrt(0.5)
    # pylint: enable=invalid-name

    band_offset = band_width * math.sqrt(0.5)

    if mark_radius is not None:
        top_face_func = lambda vertices: make_body_cap(vertices, mark_radius, mark_offset,
            mark_resolution)
    else:
        top_face_func = default_quad_face_functor

    vertices = [
        numpy.array([     x,  y - r, z]),
        numpy.array([ x - r,      y, z]),
        numpy.array([-x + r,      y, z]),
        numpy.array([    -x,  y - r, z]),
        numpy.array([    -x, -y + r, z]),
        numpy.array([-x + r,     -y, z]),
        numpy.array([ x - r,     -y, z]),
        numpy.array([     x, -y + r, z]),

        numpy.array([     x + band_offset,  y - r + band_offset, band]),
        numpy.array([ x - r + band_offset,      y + band_offset, band]),
        numpy.array([-x + r - band_offset,      y + band_offset, band]),
        numpy.array([    -x - band_offset,  y - r + band_offset, band]),
        numpy.array([    -x - band_offset, -y + r - band_offset, band]),
        numpy.array([-x + r - band_offset,     -y - band_offset, band]),
        numpy.array([ x - r + band_offset,     -y - band_offset, band]),
        numpy.array([     x + band_offset, -y + r - band_offset, band]),

        numpy.array([     x,  y - r, -z]),
        numpy.array([ x - r,      y, -z]),
        numpy.array([-x + r,      y, -z]),
        numpy.array([    -x,  y - r, -z]),
        numpy.array([    -x, -y + r, -z]),
        numpy.array([-x + r,     -y, -z]),
        numpy.array([ x - r,     -y, -z]),
        numpy.array([     x, -y + r, -z])]
    edges = [
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
        [15, 23]]
    faces = [
        # Top
        [0, 1, 2, 3],
        ([0, 3, 4, 7], top_face_func),
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

    body = round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=line_resolution)

    if mark_radius is not None:
        mark = make_body_mark(mark_radius, mark_resolution)
        mark.translate(numpy.array([*mark_offset, z]))
        mark.apply()
    else:
        mark = None
    return (body, mark)

def make_sloped_box(size, chamfer, slope, slope_height, edge_resolution, line_resolution,
                    band=None, band_width=0.0):
    if band is None:
        raise Exception() # TODO

    x, y, z = numpy.array(size) / 2.0 # pylint: disable=invalid-name
    z_mean = z - slope_height
    y_slope = y - slope_height / math.tan(slope)

    band_offset = band_width * math.sqrt(0.5)
    offset = band_offset - z_mean * (band_offset / z)
    x_mean = x + offset
    y_mean = y + offset

    vertices = [
        numpy.array([ x,  y, -z]),
        numpy.array([-x,  y, -z]),
        numpy.array([-x, -y, -z]),
        numpy.array([ x, -y, -z]),

        numpy.array([ x + band_offset,  y + band_offset, band]),
        numpy.array([-x - band_offset,  y + band_offset, band]),
        numpy.array([-x - band_offset, -y - band_offset, band]),
        numpy.array([ x + band_offset, -y - band_offset, band]),

        numpy.array([ x_mean, y_mean, z_mean]),
        numpy.array([-x_mean, y_mean, z_mean]),

        numpy.array([ x, y_slope, z]),
        numpy.array([-x, y_slope, z]),
        numpy.array([-x, -y, z]),
        numpy.array([ x, -y, z])]
    edges = [
        [0, 1, 2, 3, 0],
        [4, 5, 6, 7, 4],
        [8, 9],
        [10, 11, 12, 13, 10],
        [3, 7, 13], [10, 8, 4, 0],
        [2, 6, 12], [11, 9, 5, 1]]
    faces = [
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
        [7, 8, 10, 13]]

    return round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=line_resolution)

def make_rounded_rect(size, roundness, segments):
    # pylint: disable=invalid-name
    dx, dy = size[0] / 2.0, size[1] / 2.0
    r, rb = roundness, roundness * calc_bezier_weight(angle=math.pi / 2.0)
    # pylint: enable=invalid-name

    shape = []
    shape.append(curves.Line((-dx + r, dy, 0.0), (dx - r, dy, 0.0), 1))
    shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                               (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
    shape.append(curves.Line((dx, dy - r, 0.0), (dx, -dy + r, 0.0), 1))
    shape.append(curves.Bezier((dx, -dy + r, 0.0), (0.0, -rb, 0.0),
                               (dx - r, -dy, 0.0), (rb, 0.0, 0.0), segments))
    shape.append(curves.Line((dx - r, -dy, 0.0), (-dx + r, -dy, 0.0), 1))
    shape.append(curves.Bezier((-dx + r, -dy, 0.0), (-rb, 0.0, 0.0),
                               (-dx, -dy + r, 0.0), (0.0, -rb, 0.0), segments))
    shape.append(curves.Line((-dx, -dy + r, 0.0), (-dx, dy - r, 0.0), 1))
    shape.append(curves.Bezier((-dx, dy - r, 0.0), (0.0, rb, 0.0),
                               (-dx + r, dy, 0.0), (-rb, 0.0, 0.0), segments))

    return shape

def make_pin_curve(pin_shape_size, pin_height, pin_length, pin_slope, chamfer, roundness,
                   pivot=0.5, outer_radius_k=0.35, inner_radius_k=0.3, chamfer_resolution=2,
                   edge_resolution=3):
    curve = []

    y_mean = pin_height / 2.0
    rad_limit = min(pin_height, pin_length)
    outer_rad = outer_radius_k * rad_limit
    inner_rad = inner_radius_k * rad_limit

    outer_off = y_mean - pin_shape_size[1] / 2.0 - outer_rad * (1.0 - math.sin(pin_slope))
    inner_off = y_mean - inner_rad * (1.0 - math.sin(pin_slope))

    y_pos = [None] * 7
    y_pos[0] = pin_shape_size[1] / 2.0
    y_pos[1] = y_pos[0]
    y_pos[2] = y_pos[1]
    y_pos[3] = y_mean - outer_off
    y_pos[4] = y_mean + inner_off
    y_pos[5] = pin_height
    y_pos[6] = y_pos[5]

    x_pos = [None] * 7
    x_pos[0] = pin_length
    x_pos[1] = pin_length - chamfer
    x_pos[2] = (pin_length * pivot + outer_off * math.tan(pin_slope)
        + outer_rad * math.cos(pin_slope))
    x_pos[3] = pin_length * pivot + outer_off * math.tan(pin_slope)
    x_pos[4] = pin_length * pivot - inner_off * math.tan(pin_slope)
    x_pos[5] = (pin_length * pivot - inner_off * math.tan(pin_slope)
        - inner_rad * math.cos(pin_slope))
    x_pos[6] = 0.0

    points = [
        numpy.array([x_pos[0], 0.0, y_pos[0]]),
        numpy.array([x_pos[1], 0.0, y_pos[1]]),
        numpy.array([x_pos[2], 0.0, y_pos[2]]),
        numpy.array([x_pos[3], 0.0, y_pos[3]]),
        numpy.array([x_pos[4], 0.0, y_pos[4]]),
        numpy.array([x_pos[5], 0.0, y_pos[5]]),
        numpy.array([x_pos[6], 0.0, y_pos[6]])]

    # Control points of segment 0
    p0t1 = (points[1] - points[0]) / 3.0
    p1t0 = (points[0] - points[1]) / 3.0

    # Control points of segment 3
    lp2p3 = math.sin((math.pi / 2.0 - pin_slope) / 2.0) * numpy.linalg.norm(points[2] - points[3])
    p2t3 = numpy.array([-lp2p3, 0.0, 0.0]) * roundness
    p3t2 = lp2p3 * model.normalize(points[3] - points[4]) * roundness

    # Control points of segment 5
    lp4p5 = math.sin((math.pi / 2.0 - pin_slope) / 2.0) * numpy.linalg.norm(points[4] - points[5])
    p4t5 = lp4p5 * model.normalize(points[4] - points[3]) * roundness
    p5t4 = numpy.array([lp4p5, 0.0, 0.0]) * roundness

    curve.append(curves.Bezier(points[0], p0t1, points[1], p1t0, chamfer_resolution))
    curve.append(curves.Line(points[1], points[2], 1))
    curve.append(curves.Bezier(points[2], p2t3, points[3], p3t2, edge_resolution))
    curve.append(curves.Line(points[3], points[4], 1))
    curve.append(curves.Bezier(points[4], p4t5, points[5], p5t4, edge_resolution))
    curve.append(curves.Line(points[5], points[6], 1))

    return curve

def build_loft_mesh(slices, fill_start=True, fill_end=True):
    mesh = model.Mesh()

    number = len(slices[0])
    for points in slices:
        mesh.geo_vertices.extend(points)

    if fill_start:
        v_index = len(mesh.geo_vertices)
        mesh.geo_vertices.append(calc_median_point(slices[0]))
        for i in range(0, number - 1):
            mesh.geo_polygons.append([i, i + 1, v_index])

    for i in range(0, len(slices) - 1):
        for j in range(0, number - 1):
            mesh.geo_polygons.append([i * number + j,
                                      (i + 1) * number + j,
                                      (i + 1) * number + j + 1,
                                      i * number + j + 1])

    if fill_end:
        v_index = len(mesh.geo_vertices)
        mesh.geo_vertices.append(calc_median_point(slices[-1]))
        for i in range((len(slices) - 1) * number, len(slices) * number):
            mesh.geo_polygons.append([i, i + 1, v_index])

    return mesh

def calc_median_point(vertices):
    if len(vertices) == 0:
        raise Exception()

    max_pos = min_pos = vertices[0]
    for vertex in vertices:
        max_pos = numpy.maximum(max_pos, vertex)
        min_pos = numpy.minimum(min_pos, vertex)
    return (max_pos + min_pos) / 2.0

def make_pin_mesh(pin_shape_size, pin_height, pin_length, pin_slope, end_slope,
                  chamfer_resolution, edge_resolution):
    chamfer = min(pin_shape_size) / 10.0
    curve_roundness = calc_bezier_weight(angle=math.pi / 2.0 + pin_slope)

    shape = make_rounded_rect(size=pin_shape_size, roundness=chamfer, segments=chamfer_resolution)
    shape_points = []
    for element in shape:
        shape_points.extend(element.tesselate())
    shape_points = curves.optimize(shape_points)

    path = make_pin_curve(pin_shape_size=pin_shape_size, pin_height=pin_height,
                          pin_length=pin_length, pin_slope=pin_slope,
                          chamfer=chamfer, roundness=curve_roundness, pivot=0.45,
                          chamfer_resolution=chamfer_resolution, edge_resolution=edge_resolution)
    path_points = []
    for element in path:
        path_points.extend(element.tesselate())
    path_points = curves.optimize(path_points)

    def mesh_rotation_func(position):
        current = int(position * (len(path_points) - 1))
        if current == len(path_points) - 1:
            return numpy.array([end_slope, 0.0, 0.0])
        return numpy.zeros(3)

    def mesh_scaling_func(position):
        if chamfer_resolution >= 1:
            current = int(position * (len(path_points) - 1))

            if current < chamfer_resolution:
                size = numpy.array(pin_shape_size)
                scale = (size - chamfer * 2.0) / size
                t_seg = math.sin((math.pi / 2.0) * (current / chamfer_resolution))
                t_scale = scale + (numpy.array([1.0, 1.0]) - scale) * t_seg
                return numpy.array([*t_scale, 1.0])
            return numpy.ones(3)
        return numpy.ones(3)

    slices = curves.loft(path=path_points, shape=shape_points, rotation=mesh_rotation_func,
                         scaling=mesh_scaling_func)
    return build_loft_mesh(slices, True, False)
