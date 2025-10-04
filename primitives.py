#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# primitives.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import curves
from wrlconv import geometry
from wrlconv import model

def calc_bezier_weight(a=None, b=None, angle=None): # pylint: disable=invalid-name
    if angle is None:
        if a is None or b is None:
            # User must provide vectors a and b when angle argument is not used
            raise TypeError()
        angle = model.angle(a, b)

    return (4.0 / 3.0) * math.tan(angle / 4.0)

def calc_median_point(vertices):
    if len(vertices) == 0:
        raise ValueError()

    max_pos = min_pos = vertices[0]
    for vertex in vertices:
        max_pos = numpy.maximum(max_pos, vertex)
        min_pos = numpy.minimum(min_pos, vertex)
    return (max_pos + min_pos) / 2.0

def hmils(values):
    # Convert millimeters to hundreds of mils
    try:
        return numpy.array([value / 2.54 for value in values])
    except TypeError:
        return values / 2.54

def limit_vector_pair(a, b): # pylint: disable=invalid-name
    ab_sum = a + b
    a_proj_ab, b_proj_ab = reverse_projection(a, ab_sum), reverse_projection(b, ab_sum)
    if numpy.linalg.norm(a_proj_ab) > numpy.linalg.norm(b_proj_ab):
        ab_part = a_proj_ab
    else:
        ab_part = b_proj_ab
    scale = numpy.linalg.norm(ab_part) / numpy.linalg.norm(ab_sum)
    return a * scale, b * scale

def projection(a, b): # pylint: disable=invalid-name
    # Return projection of a vector a in the direction of a vector b
    b_norm = model.normalize(b)
    return numpy.dot(a, b_norm) * b_norm

def round1f(value):
    if int(value * 10) == int(value) * 10:
        return f'{int(value):d}'
    return f'{value:.1f}'

def round2f(value):
    if int(value * 100) == int(value * 10) * 10:
        return f'{value:.1f}'
    return f'{value:.2f}'

def reorder_points(edge, origin):
    return [edge[1], edge[0]] if edge[1] == origin else edge

def reverse_projection(a, b): # pylint: disable=invalid-name
    a_norm = model.normalize(a)
    b_norm = model.normalize(b)
    dot = numpy.dot(a_norm, b_norm)

    if dot == 0.0:
        # Two segments are orthogonal
        raise ValueError()
    return (numpy.linalg.norm(a) / dot) * b_norm

def sort_edge_points(points):
    return (min(points), max(points))

def default_quad_face_functor(points, resolution=(1, 1), inversion=False, roundness=1.0 / 3.0):
    p01_vec = (points[1] - points[0]) * roundness
    p03_vec = (points[3] - points[0]) * roundness
    p21_vec = (points[1] - points[2]) * roundness
    p23_vec = (points[3] - points[2]) * roundness

    p10_vec = -p01_vec
    p12_vec = -p21_vec
    p30_vec = -p03_vec
    p32_vec = -p23_vec

    line0 = (points[1], points[1] + p10_vec, points[0] + p01_vec, points[0])
    edge1 = (points[1] + p12_vec, points[0] + p03_vec)
    edge2 = (points[2] + p21_vec, points[3] + p30_vec)
    line3 = (points[2], points[2] + p23_vec, points[3] + p32_vec, points[3])

    line1 = (
        edge1[0],
        edge1[0] + (edge1[1] - edge1[0]) * roundness,
        edge1[1] + (edge1[0] - edge1[1]) * roundness,
        edge1[1]
    )
    line2 = (
        edge2[0],
        edge2[0] + (edge2[1] - edge2[0]) * roundness,
        edge2[1] + (edge2[0] - edge2[1]) * roundness,
        edge2[1]
    )

    return curves.BezierQuad(line0, line1, line2, line3, resolution, inversion)

def default_tri_face_functor(points, resolution=1, inversion=False, roundness=1.0 / 3.0):
    return curves.BezierTri(
        (
            points[0],
            points[0] + (points[2] - points[0]) * roundness,
            points[0] + (points[1] - points[0]) * roundness
        ), (
            points[2],
            points[2] + (points[1] - points[2]) * roundness,
            points[2] + (points[0] - points[2]) * roundness
        ), (
            points[1],
            points[1] + (points[0] - points[1]) * roundness,
            points[1] + (points[2] - points[1]) * roundness
        ),
        (points[0] + points[1] + points[2]) / 3.0,
        resolution, inversion
    )


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
    def __init__(self, vertices, num, neighbors, chamfers):
        self.num = num
        self.pos = vertices[self.num]

        u_num, v_num, w_num = neighbors[0], neighbors[1], neighbors[2]

        u_vec = vertices[u_num] - self.pos
        v_vec = vertices[v_num] - self.pos
        w_vec = vertices[w_num] - self.pos

        try:
            u_chamfer = chamfers[0]
            v_chamfer = chamfers[1]
            w_chamfer = chamfers[2]
        except TypeError:
            u_chamfer = chamfers
            v_chamfer = chamfers
            w_chamfer = chamfers

        # pylint: disable=invalid-name
        self.u = JointEdge(u_num, u_vec, w_num, w_vec, v_num, v_vec, u_chamfer)
        self.v = JointEdge(v_num, v_vec, w_num, w_vec, u_num, u_vec, v_chamfer)
        self.w = JointEdge(w_num, w_vec, v_num, v_vec, u_num, u_vec, w_chamfer)
        # pylint: enable=invalid-name

        self.u.shrink(self.v)
        self.u.shrink(self.w)
        self.v.shrink(self.w)

        self.edges = {}
        self.edges[self.u.num] = self.u
        self.edges[self.v.num] = self.v
        self.edges[self.w.num] = self.w

    def face_point(self, keys):
        return (
            self.pos
            + self.edges[keys[0]].normals[keys[1]]
            + self.edges[keys[1]].normals[keys[0]]
        )

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

        # TODO Replace 0.114 with calculated value
        return curves.BezierTri(
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
            resolution, inversion
        )

    def nearest_face(self, p0, p1, constraints=None): # pylint: disable=invalid-name
        pairs = [(self.u.num, self.v.num), (self.u.num, self.w.num), (self.v.num, self.w.num)]

        if constraints is not None:
            for constraint in constraints:
                for pair in pairs:
                    if constraint not in pair:
                        pairs.remove(pair)
                        break

        raw_normal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face_point(pair) for pair in pairs]
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

        def set_roundness(self, roundness):
            self.u.roundness = roundness
            self.v.roundness = roundness


    def __init__(self, vertices, num, neighbors, chamfers, sharpness):
        self.num = num
        self.pos = vertices[self.num]

        try:
            values = {neighbors[i]: chamfers[i] for i in range(0, len(neighbors))}
        except TypeError:
            values = {neighbors[i]: chamfers for i in range(0, neighbors)}

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
        angles = (
            model.angle(vecs[sections[0][0]], vecs[sections[0][1]]),
            model.angle(vecs[sections[1][0]], vecs[sections[1][1]])
        )

        self.flat0 = angles[0] > sharpness
        self.flat1 = angles[1] > sharpness

        if self.flat0:
            self.diag0 = QuadJoint.Diag(
                JointEdge(
                    sections[1][0], vecs[sections[1][0]],
                    sections[0][0], numpy.zeros(3),
                    sections[0][1], numpy.zeros(3),
                    values[sections[1][0]]
                ),
                JointEdge(
                    sections[1][1], vecs[sections[1][1]],
                    sections[0][0], numpy.zeros(3),
                    sections[0][1], numpy.zeros(3),
                    values[sections[1][1]]
                )
            )
        else:
            self.diag0 = QuadJoint.Diag(
                JointEdge(
                    sections[1][0], vecs[sections[1][0]],
                    sections[0][0], vecs[sections[0][0]],
                    sections[0][1], vecs[sections[0][1]],
                    values[sections[1][0]], not self.flat1
                ),
                JointEdge(
                    sections[1][1], vecs[sections[1][1]],
                    sections[0][0], vecs[sections[0][0]],
                    sections[0][1], vecs[sections[0][1]],
                    values[sections[1][1]], not self.flat1
                )
            )

        if self.flat1:
            self.diag1 = QuadJoint.Diag(
                JointEdge(
                    sections[0][0], vecs[sections[0][0]],
                    sections[1][0], numpy.zeros(3),
                    sections[1][1], numpy.zeros(3),
                    values[sections[0][0]]
                ),
                JointEdge(
                    sections[0][1], vecs[sections[0][1]],
                    sections[1][0], numpy.zeros(3),
                    sections[1][1], numpy.zeros(3),
                    values[sections[0][1]]
                )
            )
        else:
            self.diag1 = QuadJoint.Diag(
                JointEdge(
                    sections[0][0], vecs[sections[0][0]],
                    sections[1][0], vecs[sections[1][0]],
                    sections[1][1], vecs[sections[1][1]],
                    values[sections[0][0]], not self.flat0
                ),
                JointEdge(
                    sections[0][1], vecs[sections[0][1]],
                    sections[1][0], vecs[sections[1][0]],
                    sections[1][1], vecs[sections[1][1]],
                    values[sections[0][1]], not self.flat0
                )
            )

        roundness0 = calc_bezier_weight(angle=abs(angles[0]))
        self.diag0.set_roundness(roundness0)
        roundness1 = calc_bezier_weight(angle=abs(angles[1]))
        self.diag1.set_roundness(roundness1)

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

    def face_point(self, keys):
        return (
            self.pos
            + self.edges[keys[0]].normals[keys[1]]
            + self.edges[keys[1]].normals[keys[0]]
        )

    def mesh(self, resolution, inversion=False):
        if self.flat0 or self.flat1:
            return None

        corners = [
            self.diag0.u.m + self.diag1.u.m,
            self.diag0.u.n + self.diag1.v.m,
            self.diag0.v.n + self.diag1.v.n,
            self.diag0.v.m + self.diag1.u.n
        ]
        inversion = inversion ^ (numpy.linalg.det(numpy.array([*corners[0:3]])) < 0.0)

        return curves.BezierQuad(
            (
                self.pos + corners[0],
                self.pos + corners[0] - self.diag0.u.m * self.diag0.u.roundness,
                self.pos + corners[1] - self.diag0.u.n * self.diag0.u.roundness,
                self.pos + corners[1]
            ), (
                self.pos + corners[0] - self.diag1.u.m * self.diag1.u.roundness,
                self.pos + corners[0]
                    - self.diag1.u.m * self.diag1.u.roundness
                    - self.diag0.u.m * self.diag0.u.roundness,
                self.pos + corners[1]
                    - self.diag1.v.m * self.diag1.v.roundness
                    - self.diag0.u.n * self.diag0.u.roundness,
                self.pos + corners[1] - self.diag1.v.m * self.diag1.v.roundness
            ), (
                self.pos + corners[3] - self.diag1.u.n * self.diag1.u.roundness,
                self.pos + corners[3]
                    - self.diag1.u.n * self.diag1.u.roundness
                    - self.diag0.v.m * self.diag0.v.roundness,
                self.pos + corners[2]
                    - self.diag1.v.n * self.diag1.v.roundness
                    - self.diag0.v.n * self.diag0.v.roundness,
                self.pos + corners[2] - self.diag1.v.n * self.diag1.v.roundness
            ), (
                self.pos + corners[3],
                self.pos + corners[3] - self.diag0.v.m * self.diag0.v.roundness,
                self.pos + corners[2] - self.diag0.v.n * self.diag0.v.roundness,
                self.pos + corners[2]
            ),
            resolution, inversion
        )

    def nearest_face(self, p0, p1, constraints=None): # pylint: disable=invalid-name
        pairs = [
            (self.diag0.u.num, self.diag1.u.num),
            (self.diag0.u.num, self.diag1.v.num),
            (self.diag0.v.num, self.diag1.v.num),
            (self.diag0.v.num, self.diag1.u.num)
        ]

        if constraints is not None:
            for constraint in constraints:
                for pair in pairs:
                    if constraint not in pair:
                        pairs.remove(pair)
                        break

        raw_normal = numpy.cross(p0 - self.pos, p1 - self.pos)
        positions = [self.face_point(pair) for pair in pairs]
        normals = [numpy.cross(p0 - x, p1 - x) for x in positions]
        angles = [model.angle(raw_normal, x) for x in normals]
        return pairs[angles.index(min(angles))]


def append_hollow_cap(mesh, outer, inner, normal):
    inner_mean = numpy.zeros(3)
    for vertex in inner.values():
        inner_mean += vertex
    inner_mean /= len(inner)

    direction = inner[next(iter(inner))] - inner_mean
    inner_indices = geometry.sort_vertices_by_angle(inner, inner_mean, normal, direction)
    outer_indices = geometry.sort_vertices_by_angle(outer, inner_mean, normal, direction)

    i_count, o_count = len(inner_indices), len(outer_indices)
    i_index, o_index = 0, 0
    i_offset = len(mesh.geo_vertices)
    polygons = []

    while o_index < o_count:
        if o_index < o_count - 1:
            threshold = (outer_indices[o_index + 1][1] + outer_indices[o_index][1]) / 2.0
        else:
            threshold = outer_indices[o_index][1]

        while i_index < i_count and (inner_indices[i_index][1] < threshold
                                     or o_index == o_count - 1):
            polygons.append([
                outer_indices[o_index][0],
                inner_indices[(i_index + 1) % i_count][0] + i_offset,
                inner_indices[i_index][0] + i_offset
            ])
            i_index += 1

        polygons.append([
            outer_indices[o_index][0],
            outer_indices[(o_index + 1) % o_count][0],
            inner_indices[i_index % i_count][0] + i_offset
        ])
        o_index += 1

    for vertex in inner.values():
        mesh.geo_vertices.append(vertex)
    mesh.geo_polygons.extend(polygons)

def append_solid_cap(mesh, vertices, origin=None, normal=None):
    if origin is None and normal is None:
        raise ValueError()

    mean = numpy.zeros(3)
    for vertex in vertices.values():
        mean += vertex
    mean /= len(vertices)

    if normal is None:
        normal = model.normalize(mean - origin)

    indices = [x[0] for x in geometry.sort_vertices_by_angle(vertices, mean, normal)]
    mean_index = len(mesh.geo_vertices)
    mesh.geo_vertices.append(mean)

    count = len(indices)
    polygons = []
    for i in range(0, count):
        polygons.append([indices[i % count], indices[(i + 1) % count], mean_index])
    mesh.geo_polygons.extend(polygons)

def make_body_cap(corners, radius, offset, edges, resolution=(1, 1)):
    if edges % 4 != 0:
        raise ValueError()
    if len(corners) != 4:
        raise ValueError()

    mesh = model.Mesh()
    mean = sum(corners) / len(corners)
    circle_offset = mean + numpy.array([*offset, 0.0])

    outer_vertices = geometry.make_bezier_quad_outline(corners, resolution)
    inner_vertices = geometry.make_circle_outline(circle_offset, radius, edges)

    for vertex in outer_vertices.values():
        mesh.geo_vertices.append(vertex)
    append_hollow_cap(mesh, outer_vertices, inner_vertices, numpy.array([0.0, 0.0, 1.0]))
    return mesh

def make_rounded_edge(beg, end, resolution, inversion=False, roundness=1.0 / 3.0):
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

    direction = (end_pos_m + end_pos_n) - (beg_pos_m + beg_pos_n)
    if numpy.linalg.det(numpy.array([beg_dir_m, beg_dir_n, direction])) > 0.0:
        beg_dir_m, beg_dir_n = beg_dir_n, beg_dir_m
        beg_pos_m, beg_pos_n = beg_pos_n, beg_pos_m
    if numpy.linalg.det(numpy.array([end_dir_m, end_dir_n, direction])) < 0.0:
        end_dir_m, end_dir_n = end_dir_n, end_dir_m
        end_pos_m, end_pos_n = end_pos_n, end_pos_m

    line0 = (
        beg_pos_n + beg_dir_n,
        beg_pos_n + beg_dir_n * (1.0 - beg_roundness),
        beg_pos_m + beg_dir_m * (1.0 - beg_roundness),
        beg_pos_m + beg_dir_m
    )
    line3 = (
        end_pos_m + end_dir_m,
        end_pos_m + end_dir_m * (1.0 - end_roundness),
        end_pos_n + end_dir_n * (1.0 - end_roundness),
        end_pos_n + end_dir_n
    )

    line1 = (
        line0[0] + (line3[0] - line0[0]) * roundness,
        line0[1] + (line3[1] - line0[1]) * roundness,
        line0[2] + (line3[2] - line0[2]) * roundness,
        line0[3] + (line3[3] - line0[3]) * roundness
    )
    line2 = (
        line3[0] + (line0[0] - line3[0]) * roundness,
        line3[1] + (line0[1] - line3[1]) * roundness,
        line3[2] + (line0[2] - line3[2]) * roundness,
        line3[3] + (line0[3] - line3[3]) * roundness
    )

    return curves.BezierQuad(line0, line1, line2, line3, resolution, inversion)

def round_model_edges(vertices, edges, faces, chamfer, sharpness, edge_resolution, line_resolution):
    meshes = []
    processed_edges = []
    tessellated_edges = []
    vertex_counters = {}

    for edge_info in edges:
        if isinstance(edge_info, tuple):
            edge_vertices = edge_info[0]
            edge_weight = edge_info[1]
            edge_details = edge_info[2]
        else:
            edge_vertices = edge_info
            edge_weight = 1.0
            edge_details = line_resolution

        for i in range(0, len(edge_vertices) - 1):
            tessellated_edges.append((
                (edge_vertices[i], edge_vertices[i + 1]),
                edge_weight,
                edge_details
            ))

    for edge_vertices, _1, _2 in tessellated_edges:
        for vertex in edge_vertices:
            if vertex in vertex_counters:
                vertex_counters[vertex] += 1
            else:
                vertex_counters[vertex] = 1

    def get_edge_resolution(key):
        for edge_vertices, _, edge_details in tessellated_edges:
            if sort_edge_points(edge_vertices) == key:
                return edge_details
        return line_resolution

    joints = {}

    # Make intersections of three edges
    tri_joint_indices = filter(lambda x: vertex_counters[x] == 3, vertex_counters)

    for vertex in tri_joint_indices:
        chamfers = []
        neighbors = []
        for edge_vertices, edge_weight, _ in tessellated_edges:
            if vertex in edge_vertices:
                chamfers.append(chamfer * edge_weight)
                neighbors.append(reorder_points(edge_vertices, vertex)[1])
        joints[vertex] = TriJoint(vertices, vertex, neighbors, chamfers)
        mesh = joints[vertex].mesh(edge_resolution)
        if mesh is not None:
            meshes.append(mesh)

    # Make intersections of four edges
    quad_joint_indices = filter(lambda x: vertex_counters[x] == 4, vertex_counters)

    for vertex in quad_joint_indices:
        chamfers = []
        neighbors = []
        for edge_vertices, edge_weight, _ in tessellated_edges:
            if vertex in edge_vertices:
                chamfers.append(chamfer * edge_weight)
                neighbors.append(reorder_points(edge_vertices, vertex)[1])
        joints[vertex] = QuadJoint(vertices, vertex, neighbors, chamfers, sharpness)
        mesh = joints[vertex].mesh((edge_resolution, edge_resolution))
        if mesh is not None:
            meshes.append(mesh)

    for vertex in joints:
        for key in joints[vertex].edges:
            uname = sort_edge_points((vertex, key))
            if uname in processed_edges:
                continue
            processed_edges.append(uname)

            try:
                beg_joint = joints[vertex]
                end_joint = joints[key]
                seg_resolution = get_edge_resolution(uname)
                mesh = make_rounded_edge(beg_joint, end_joint, (seg_resolution, edge_resolution))
                if mesh is not None:
                    meshes.append(mesh)
            except KeyError:
                pass

    for entry in faces:
        try:
            indices, count = entry[0], len(entry[0])
            functor = lambda points, _, face=entry: face[1](points)
        except TypeError:
            indices, count = entry, len(entry)
            if count == 4:
                functor = lambda points, resolution: default_quad_face_functor(points=points,
                    resolution=resolution)
            else:
                functor = lambda points, resolution: default_tri_face_functor(points=points,
                    resolution=resolution)

        face_details = []
        face_vertices = []

        for i in range(0, count):
            next_edge, prev_edge = indices[(i + 1) % count], indices[i - 1]
            joint = joints[indices[i]]

            face_details.append(get_edge_resolution(sort_edge_points((prev_edge, indices[i]))))

            constraints = []
            if next_edge in joint.edges:
                constraints.append(next_edge)
            if prev_edge in joint.edges:
                constraints.append(prev_edge)

            nearest = joint.nearest_face(vertices[prev_edge], vertices[next_edge], constraints)
            face_vertices.append(joint.face_point(nearest))

        if len(face_details) == 3:
            if face_details[0] != face_details[1] or face_details[1] != face_details[2]:
                raise ValueError()
            face_resolution = face_details[0]
        else:
            if face_details[0] != face_details[2] or face_details[1] != face_details[3]:
                raise ValueError()
            face_resolution = (face_details[0], face_details[1])

        meshes.append(functor(face_vertices, face_resolution))

    # Build resulting mesh
    mesh = model.Mesh()
    for part in meshes:
        mesh.append(part)
    mesh.optimize()

    return mesh

def make_box(size, chamfer, edge_resolution, line_resolution, band_size=None, band_offset=0.0,
             mark_radius=None, mark_offset=numpy.zeros(2), mark_resolution=24):
    try:
        resolutions = (line_resolution[0], line_resolution[1], line_resolution[2])
        # TODO Select default resolution
        default_resolution = max(resolutions)
    except TypeError:
        resolutions = (line_resolution, line_resolution, line_resolution)
        default_resolution = line_resolution

    if mark_radius is not None:
        top_face_func = lambda points: make_body_cap(points, mark_radius, mark_offset,
            mark_resolution, (resolutions[0], resolutions[1]))
    else:
        top_face_func = None

    x, y, z = numpy.array(size) / 2.0 # pylint: disable=invalid-name

    vertices = [
        numpy.array([ x,  y, z]),
        numpy.array([-x,  y, z]),
        numpy.array([-x, -y, z]),
        numpy.array([ x, -y, z]),

        numpy.array([ x,  y, -z]),
        numpy.array([-x,  y, -z]),
        numpy.array([-x, -y, -z]),
        numpy.array([ x, -y, -z])
    ]
    edges = [
        # Top
        ([0, 1], 1.0, resolutions[0]),
        ([1, 2], 1.0, resolutions[1]),
        ([2, 3], 1.0, resolutions[0]),
        ([3, 0], 1.0, resolutions[1]),
        # Bottom
        ([4, 5], 1.0, resolutions[0]),
        ([5, 6], 1.0, resolutions[1]),
        ([6, 7], 1.0, resolutions[0]),
        ([7, 4], 1.0, resolutions[1])
    ]
    faces = [
        # Bottom
        [7, 6, 5, 4]
    ]

    # Top
    if top_face_func is not None:
        faces.append(([0, 1, 2, 3], top_face_func))
    else:
        faces.append([0, 1, 2, 3])

    if band_size is not None:
        band_offset_xy = band_size * math.sqrt(0.5)
        band_offset_z = band_offset

        vertices.extend([
            numpy.array([ x + band_offset_xy,  y + band_offset_xy, band_offset_z]),
            numpy.array([-x - band_offset_xy,  y + band_offset_xy, band_offset_z]),
            numpy.array([-x - band_offset_xy, -y - band_offset_xy, band_offset_z]),
            numpy.array([ x + band_offset_xy, -y - band_offset_xy, band_offset_z])
        ])
        edges.extend([
            # Middle
            ([8, 9], 1.0, resolutions[0]),
            ([9, 10], 1.0, resolutions[1]),
            ([10, 11], 1.0, resolutions[0]),
            ([11, 8], 1.0, resolutions[1]),
            # Sides, upper half
            ([0, 8], 1.0, resolutions[2]),
            ([1, 9], 1.0, resolutions[2]),
            ([2, 10], 1.0, resolutions[2]),
            ([3, 11], 1.0, resolutions[2]),
            # Sides, lower half
            ([8, 4], 1.0, resolutions[2]),
            ([9, 5], 1.0, resolutions[2]),
            ([10, 6], 1.0, resolutions[2]),
            ([11, 7], 1.0, resolutions[2])
        ])
        faces.extend([
            # Sides, upper half
            [8, 9, 1, 0],
            [9, 10, 2, 1],
            [10, 11, 3, 2],
            [11, 8, 0, 3],
            # Sides, lower half
            [4, 5, 9, 8],
            [5, 6, 10, 9],
            [6, 7, 11, 10],
            [7, 4, 8, 11]
        ])
    else:
        edges.extend([
            # Sides
            ([0, 4], 1.0, resolutions[2]),
            ([1, 5], 1.0, resolutions[2]),
            ([2, 6], 1.0, resolutions[2]),
            ([3, 7], 1.0, resolutions[2])
        ])
        faces.extend([
            # Sides
            [4, 5, 1, 0],
            [5, 6, 2, 1],
            [6, 7, 3, 2],
            [7, 4, 0, 3]
        ])

    body = round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=default_resolution)
    return body

def make_chip_body(size, chamfer, edge_resolution):
    x_half = size[0] / 2.0
    y, z = size[1], size[2] # pylint: disable=invalid-name

    path_points = [
        numpy.array([x_half, 0.0, 0.0]),
        numpy.array([-x_half, 0.0, 0.0])]

    shape = make_rounded_rect(size=numpy.array([z, y]), roundness=chamfer,
                              segments=edge_resolution)
    shape_points = []
    for element in shape:
        shape_points.extend(element.tessellate())
    shape_points = curves.optimize(shape_points)

    slices = curves.loft(path=path_points, shape=shape_points)
    return build_loft_mesh(slices, False, False)

def make_chip_lead_cap(size, chamfer, invert, edge_resolution, line_resolution, axis):
    x, y, z = numpy.array(size) / 2.0 # pylint: disable=invalid-name

    vertices = [
        numpy.array([ x,  y, -z]),
        numpy.array([-x,  y, -z]),
        numpy.array([-x, -y, -z]),
        numpy.array([ x, -y, -z]),

        numpy.array([ x,  y, z]),
        numpy.array([-x,  y, z]),
        numpy.array([-x, -y, z]),
        numpy.array([ x, -y, z])
    ]

    edges = []
    faces = []

    if axis == 0:
        edges.extend([[1, 0], [2, 3], [5, 4], [6, 7]])
        if invert:
            edges.append([1, 2, 6, 5, 1])
            faces.append([1, 2, 6, 5])
        else:
            edges.append([3, 0, 4, 7, 3])
            faces.append([3, 0, 4, 7])
    elif axis == 1:
        edges.extend([[2, 1], [3, 0], [6, 5], [7, 4]])
        if invert:
            edges.append([2, 3, 7, 6, 2])
            faces.append([2, 3, 7, 6])
        else:
            edges.append([0, 1, 5, 4, 0])
            faces.append([0, 1, 5, 4])
    else:
        edges.extend([[0, 4], [1, 5], [2, 6], [3, 7]])
        if invert:
            edges.append([0, 1, 2, 3, 0])
            faces.append([0, 1, 2, 3])
        else:
            edges.append([4, 5, 6, 7, 4])
            faces.append([4, 5, 6, 7])

    return round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=line_resolution)

def make_chip_lead_slope(case_size, lead_size, case_chamfer, lead_chamfer, invert,
                         edge_resolution, line_resolution):
    roundness = lead_chamfer / math.sqrt(2.0)
    x_lead_half = lead_size[0] / 2.0
    y_case, z_case = case_size[1], case_size[2]
    y_lead, z_lead = lead_size[1], lead_size[2]

    if invert:
        p0 = numpy.array([-x_lead_half + roundness, 0.0, 0.0])
        p1 = numpy.array([x_lead_half - roundness, 0.0, 0.0])
        p2 = numpy.array([x_lead_half, 0.0, 0.0])
    else:
        p0 = numpy.array([x_lead_half - roundness, 0.0, 0.0])
        p1 = numpy.array([-x_lead_half + roundness, 0.0, 0.0])
        p2 = numpy.array([-x_lead_half, 0.0, 0.0])

    path = []
    path.append(curves.Line(p0, p1, line_resolution))
    path.append(curves.Bezier(p1, (p2 - p1) / 3.0, p2, (p1 - p2) / 3.0, edge_resolution))

    path_points = []
    for element in path:
        path_points.extend(element.tessellate())
    path_points = curves.optimize(path_points)

    case_shape = make_rounded_rect(size=numpy.array([z_case, y_case]),
                                   roundness=case_chamfer, segments=edge_resolution)
    case_points = []
    for element in case_shape:
        case_points.extend(element.tessellate())
    case_points = curves.optimize(case_points)

    lead_shape = make_rounded_rect(size=numpy.array([z_lead, y_lead]),
                                   roundness=roundness, segments=edge_resolution)
    lead_points = []
    for element in lead_shape:
        lead_points.extend(element.tessellate())
    lead_points = curves.optimize(lead_points)

    def mesh_morphing_func(number):
        if number >= line_resolution:
            number = edge_resolution - (number - line_resolution)
            t_pos = math.sin((math.pi / 2.0) * (number / edge_resolution))
            points = []
            for i, point in enumerate(case_points):
                points.append(point + (lead_points[i] - point) * t_pos)
            return points
        return lead_points

    slices = curves.loft(path=path_points, shape=None, morphing=mesh_morphing_func)
    return build_loft_mesh(slices, False, False)

def make_chip_leads(case_size, lead_size, case_chamfer, lead_chamfer, edge_resolution,
                    line_resolution):
    mesh_a = make_chip_lead_cap(size=lead_size, chamfer=lead_chamfer, invert=False,
                                edge_resolution=edge_resolution, line_resolution=line_resolution,
                                axis=0)
    mesh_a.translate(numpy.array([(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))
    slope_a = make_chip_lead_slope(case_size=case_size, lead_size=lead_size,
                                   case_chamfer=case_chamfer, lead_chamfer=lead_chamfer,
                                   invert=False, edge_resolution=edge_resolution,
                                   line_resolution=line_resolution)
    slope_a.translate(numpy.array([(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))

    mesh_b = make_chip_lead_cap(size=lead_size, chamfer=lead_chamfer, invert=True,
                                edge_resolution=edge_resolution, line_resolution=line_resolution,
                                axis=0)
    mesh_b.translate(numpy.array([-(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))
    slope_b = make_chip_lead_slope(case_size=case_size, lead_size=lead_size,
                                   case_chamfer=case_chamfer, lead_chamfer=lead_chamfer,
                                   invert=True, edge_resolution=edge_resolution,
                                   line_resolution=line_resolution)
    slope_b.translate(numpy.array([-(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))

    mesh = model.Mesh()
    mesh.append(mesh_a)
    mesh.append(mesh_b)
    mesh.append(slope_a)
    mesh.append(slope_b)
    mesh.optimize()
    return mesh

def make_rounded_box(size, roundness, chamfer, edge_resolution, line_resolution, band_size=None,
                     band_offset=0.0, mark_radius=None, mark_offset=numpy.zeros(2),
                     mark_resolution=24):
    if band_size is None:
        raise ValueError() # TODO

    # pylint: disable=invalid-name
    x, y, z = numpy.array(size) / 2.0
    r = roundness * math.sqrt(0.5)
    # pylint: enable=invalid-name

    band_offset_xy = band_size * math.sqrt(0.5)
    band_offset_z = band_offset

    if mark_radius is not None:
        top_face_func = lambda points: make_body_cap(points, mark_radius, mark_offset,
            mark_resolution, (line_resolution, line_resolution))
    else:
        top_face_func = None

    vertices = [
        numpy.array([     x,  y - r, z]),
        numpy.array([ x - r,      y, z]),
        numpy.array([-x + r,      y, z]),
        numpy.array([    -x,  y - r, z]),
        numpy.array([    -x, -y + r, z]),
        numpy.array([-x + r,     -y, z]),
        numpy.array([ x - r,     -y, z]),
        numpy.array([     x, -y + r, z]),

        numpy.array([     x + band_offset_xy,  y - r + band_offset_xy, band_offset_z]),
        numpy.array([ x - r + band_offset_xy,      y + band_offset_xy, band_offset_z]),
        numpy.array([-x + r - band_offset_xy,      y + band_offset_xy, band_offset_z]),
        numpy.array([    -x - band_offset_xy,  y - r + band_offset_xy, band_offset_z]),
        numpy.array([    -x - band_offset_xy, -y + r - band_offset_xy, band_offset_z]),
        numpy.array([-x + r - band_offset_xy,     -y - band_offset_xy, band_offset_z]),
        numpy.array([ x - r + band_offset_xy,     -y - band_offset_xy, band_offset_z]),
        numpy.array([     x + band_offset_xy, -y + r - band_offset_xy, band_offset_z]),

        numpy.array([     x,  y - r, -z]),
        numpy.array([ x - r,      y, -z]),
        numpy.array([-x + r,      y, -z]),
        numpy.array([    -x,  y - r, -z]),
        numpy.array([    -x, -y + r, -z]),
        numpy.array([-x + r,     -y, -z]),
        numpy.array([ x - r,     -y, -z]),
        numpy.array([     x, -y + r, -z])
    ]
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
        [15, 23]
    ]
    faces = [
        # Top
        [0, 1, 2, 3],
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
        [23, 16, 8, 15]
    ]

    # Top
    if top_face_func is not None:
        faces.append(([0, 3, 4, 7], top_face_func))
    else:
        faces.append([0, 3, 4, 7])

    body = round_model_edges(vertices=vertices, edges=edges, faces=faces, chamfer=chamfer,
                             sharpness=math.pi * (5.0 / 6.0), edge_resolution=edge_resolution,
                             line_resolution=line_resolution)
    return body

def make_sloped_box(size, chamfer, slope, slope_height, edge_resolution, line_resolution,
                    band_size=None, band_offset=0.0):
    if band_size is None:
        raise ValueError() # TODO

    x, y, z = numpy.array(size) / 2.0 # pylint: disable=invalid-name
    z_mean = z - slope_height
    y_slope = y - slope_height / math.tan(slope)

    band_offset_xy = band_size * math.sqrt(0.5)
    band_offset_z = band_offset
    offset = band_offset_xy - z_mean * (band_offset_xy / z)
    x_mean = x + offset
    y_mean = y + offset

    vertices = [
        numpy.array([ x,  y, -z]),
        numpy.array([-x,  y, -z]),
        numpy.array([-x, -y, -z]),
        numpy.array([ x, -y, -z]),

        numpy.array([ x + band_offset_xy,  y + band_offset_xy, band_offset_z]),
        numpy.array([-x - band_offset_xy,  y + band_offset_xy, band_offset_z]),
        numpy.array([-x - band_offset_xy, -y - band_offset_xy, band_offset_z]),
        numpy.array([ x + band_offset_xy, -y - band_offset_xy, band_offset_z]),

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

def make_rounded_rect_half(size, rotate, roundness, segments):
    # pylint: disable=invalid-name
    dx, dy = size[0], size[1]
    r, rb = roundness, roundness * calc_bezier_weight(angle=math.pi / 2.0)
    # pylint: enable=invalid-name

    shape = []
    if not rotate:
        dy /= 2.0
        shape.append(curves.Line((0.0, dy, 0.0), (dx - r, dy, 0.0), 1))
        shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                                   (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
        shape.append(curves.Line((dx, dy - r, 0.0), (dx, -dy + r, 0.0), 1))
        shape.append(curves.Bezier((dx, -dy + r, 0.0), (0.0, -rb, 0.0),
                                   (dx - r, -dy, 0.0), (rb, 0.0, 0.0), segments))
        shape.append(curves.Line((dx - r, -dy, 0.0), (0.0, -dy, 0.0), 1))
    else:
        dx /= 2.0
        shape.append(curves.Line((-dx, 0.0, 0.0), (-dx, dy - r, 0.0), 1))
        shape.append(curves.Bezier((-dx, dy - r, 0.0), (0.0, rb, 0.0),
                                   (-dx + r, dy, 0.0), (-rb, 0.0, 0.0), segments))
        shape.append(curves.Line((-dx + r, dy, 0.0), (dx - r, dy, 0.0), 1))
        shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                                   (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
        shape.append(curves.Line((dx, dy - r, 0.0), (dx, 0.0, 0.0), 1))

    return shape

def make_flat_pin_curve(pin_shape_size, pin_length, pin_offset, chamfer, chamfer_resolution=2,
                        line_resolution=1):
    curve = []

    y_pos = [pin_shape_size[1] / 2.0] * 3

    x_pos = [pin_offset] * 3
    x_pos[0] += pin_length
    x_pos[1] += pin_length - chamfer

    points = [
        numpy.array([x_pos[0], 0.0, y_pos[0]]),
        numpy.array([x_pos[1], 0.0, y_pos[1]]),
        numpy.array([x_pos[2], 0.0, y_pos[2]])
    ]

    # Control points of segment 0
    p0t1 = (points[1] - points[0]) / 3.0
    p1t0 = (points[0] - points[1]) / 3.0

    curve.append(curves.Bezier(points[0], p0t1, points[1], p1t0, chamfer_resolution))
    curve.append(curves.Line(points[1], points[2], line_resolution))

    return curve

def make_pin_curve(pin_shape_size, pin_height, pin_length, pin_slope, chamfer, roundness,
                   pivot=0.5, outer_radius_k=0.35, inner_radius_k=0.3, chamfer_resolution=2,
                   edge_resolution=3, line_resolution=1):
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
    curve.append(curves.Line(points[1], points[2], line_resolution))
    curve.append(curves.Bezier(points[2], p2t3, points[3], p3t2, edge_resolution))
    curve.append(curves.Line(points[3], points[4], line_resolution))
    curve.append(curves.Bezier(points[4], p4t5, points[5], p5t4, edge_resolution))
    curve.append(curves.Line(points[5], points[6], line_resolution))

    return curve

def build_loft_mesh(slices, fill_start=True, fill_end=True):
    mesh = model.Mesh()

    number = len(slices[0])
    for points in slices:
        mesh.geo_vertices.extend(points)

    if fill_start:
        v_center_index = len(mesh.geo_vertices)
        mesh.geo_vertices.append(calc_median_point(slices[0]))

        for i in range(0, number - 1):
            mesh.geo_polygons.append([i, i + 1, v_center_index])
        if not model.Mesh.isclose(slices[0][0], slices[0][-1]):
            # Slice is not closed, append additional polygon
            mesh.geo_polygons.append([number - 1, 0, v_center_index])

    for i in range(0, len(slices) - 1):
        for j in range(0, number - 1):
            mesh.geo_polygons.append([
                i * number + j,
                (i + 1) * number + j,
                (i + 1) * number + j + 1,
                i * number + j + 1
            ])

    if fill_end:
        v_center_index = len(mesh.geo_vertices)
        v_start_index = (len(slices) - 1) * number
        mesh.geo_vertices.append(calc_median_point(slices[-1]))

        for i in range(v_start_index, v_start_index + number - 1):
            mesh.geo_polygons.append([i + 1, i, v_center_index])
        if not model.Mesh.isclose(slices[-1][0], slices[-1][-1]):
            # Slice is not closed, append additional polygon
            mesh.geo_polygons.append([v_start_index, v_start_index + number - 1, v_center_index])

    return mesh

def make_pin_mesh(pin_shape_size, pin_height, pin_length, pin_slope, end_slope,
                  chamfer_resolution, edge_resolution, line_resolution, flat=False):
    chamfer = min(pin_shape_size) / 10.0
    curve_roundness = calc_bezier_weight(angle=math.pi / 2.0 + pin_slope)

    if flat:
        shape_correction = pin_shape_size[1] * math.cos(math.atan(end_slope))
        shape_scaling = numpy.array([1.0, pin_shape_size[1] / shape_correction, 1.0])
    else:
        shape_scaling = numpy.ones(3)

    shape = make_rounded_rect(size=numpy.array([pin_shape_size[1], pin_shape_size[0]]),
                              roundness=chamfer, segments=chamfer_resolution)
    shape_points = []
    for element in shape:
        shape_points.extend(element.tessellate())
    shape_points = curves.optimize(shape_points)

    if flat:
        length_correction = (pin_height - pin_shape_size[1] / 2.0) * end_slope
        path = make_flat_pin_curve(pin_shape_size=pin_shape_size, pin_length=pin_length,
                                   pin_offset=length_correction, chamfer=chamfer,
                                   chamfer_resolution=chamfer_resolution,
                                   line_resolution=line_resolution)
    else:
        path = make_pin_curve(pin_shape_size=pin_shape_size, pin_height=pin_height,
                              pin_length=pin_length, pin_slope=pin_slope,
                              chamfer=chamfer, roundness=curve_roundness, pivot=0.45,
                              chamfer_resolution=chamfer_resolution,
                              edge_resolution=edge_resolution, line_resolution=line_resolution)

    path_points = []
    for element in path:
        path_points.extend(element.tessellate())
    path_points = curves.optimize(path_points)

    def mesh_rotation_func(number):
        if number == len(path_points) - 1:
            return numpy.array([end_slope, 0.0, 0.0])
        return numpy.zeros(3)

    def mesh_scaling_func(number):
        if number == len(path_points) - 1:
            return shape_scaling
        if chamfer_resolution >= 1 and number < chamfer_resolution:
            shape = numpy.array(pin_shape_size)
            scale = (shape - chamfer * 2.0) / shape
            t_pos = math.sin((math.pi / 2.0) * (number / chamfer_resolution))
            t_scale = scale + (numpy.ones(2) - scale) * t_pos
            return numpy.array([*t_scale, 1.0])
        return numpy.ones(3)

    slices = curves.loft(path=path_points, shape=shape_points, rotation=mesh_rotation_func,
                         scaling=mesh_scaling_func)
    return build_loft_mesh(slices, True, False)
