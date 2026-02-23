#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# bezier.py
# Copyright (C) 2026 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from collections import deque
import itertools
import copy
import math
import numpy as np

from wrlconv import curves
from wrlconv import model

DEBUG_ENABLED = False


def make_quad_lines(points, controls, tensions=None):
    if tensions is None:
        tensions = [np.ones(2)] * len(points)

    control_points = (
        (points[0], controls[0][1] * tensions[0][1], controls[0][0] * tensions[0][0]),
        (points[1], controls[1][1] * tensions[1][1], controls[1][0] * tensions[1][0]),
        (points[2], controls[2][1] * tensions[2][1], controls[2][0] * tensions[2][0]),
        (points[3], controls[3][1] * tensions[3][1], controls[3][0] * tensions[3][0])
    )

    line_0 = (
        control_points[0][0],
        control_points[0][0] + control_points[0][1],
        control_points[1][0] + control_points[1][2],
        control_points[1][0]
    )
    line_1 = (
        control_points[0][0] + control_points[0][2],
        control_points[0][0] + control_points[0][1] + control_points[0][2],
        control_points[1][0] + control_points[1][1] + control_points[1][2],
        control_points[1][0] + control_points[1][1]
    )
    line_2 = (
        control_points[3][0] + control_points[3][1],
        control_points[3][0] + control_points[3][1] + control_points[3][2],
        control_points[2][0] + control_points[2][1] + control_points[2][2],
        control_points[2][0] + control_points[2][2]
    )
    line_3 = (
        control_points[3][0],
        control_points[3][0] + control_points[3][2],
        control_points[2][0] + control_points[2][1],
        control_points[2][0]
    )
    return (line_0, line_1, line_2, line_3)


def make_tri_vertices(points, controls, tensions=None):
    if tensions is None:
        tensions = [np.ones(2)] * len(points)

    control_points = (
        (points[0], controls[0][0] * tensions[0][0], controls[0][1] * tensions[0][1]),
        (points[1], controls[1][0] * tensions[1][0], controls[1][1] * tensions[1][1]),
        (points[2], controls[2][0] * tensions[2][0], controls[2][1] * tensions[2][1])
    )

    vertex_0 = (
        control_points[0][0],
        control_points[0][0] + control_points[0][2],
        control_points[0][0] + control_points[0][1]
    )
    vertex_1 = (
        control_points[1][0],
        control_points[1][0] + control_points[1][2],
        control_points[1][0] + control_points[1][1]
    )
    vertex_2 = (
        control_points[2][0],
        control_points[2][0] + control_points[2][2],
        control_points[2][0] + control_points[2][1]
    )
    return (vertex_0, vertex_1, vertex_2)


def default_face_functor(points, controls, resolution, inversion):
    default_tension = 1.0 / 3.0
    output_controls = []

    for b_key, b_pos in enumerate(points):
        a_key, c_key = b_key - 1, (b_key + 1) % len(points)
        current = controls[b_key]
        if current[0] is not None:
            ba_vec = current[0]
        else:
            ba_vec = (points[a_key] - b_pos) * default_tension
        if current[1] is not None:
            bc_vec = current[1]
        else:
            bc_vec = (points[c_key] - b_pos) * default_tension
        output_controls.append((ba_vec, bc_vec))

    if len(points) == 4:
        lines = make_quad_lines(points, output_controls)
        patch = curves.BezierQuad(*lines, resolution, inversion)
        return [patch]
    if len(points) == 3:
        mean = sum(points) / 3.0
        center = mean
        # center = mean - sum(control[0] for controls) * (8.0 / 9.0) # TODO
        lines = make_tri_vertices(points, output_controls)
        patch = curves.BezierTri(*lines, center, resolution, inversion)
        return [patch]
    raise ValueError()


def find_shortest_path(graph, start, end):
    if start not in graph or end not in graph:
        return None

    # Queue for BFS: stores paths (lists of nodes)
    queue = deque([[start]])
    # Set to keep track of visited nodes to avoid cycles
    visited = set([start])

    while queue:
        # Get the first path from the queue
        current_path = queue.popleft()
        current_node = current_path[-1]

        # If the current node is the end point, we found the shortest path
        if current_node == end:
            return current_path

        # Explore neighbors
        for neighbor in graph.get(current_node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                # Create a new path by appending the neighbor to the current path
                new_path = list(current_path)
                new_path.append(neighbor)
                # Add the new path to the queue
                queue.append(new_path)

    return None


def make_graph(edges):
    points = {}
    for edge in edges:
        a, b = edge
        if a in points:
            points[a].append(b)
        else:
            points[a] = [b]
        if b in points:
            points[b].append(a)
        else:
            points[b] = [a]
    return points


def make_orthogonal(v2, v1):
    # Calculate the projection of v1 onto v2 (v1_parallel)
    dot_product = np.dot(v1, v2)
    norm_sq = np.dot(v2, v2)

    if norm_sq == 0.0:
        # If v2 is a zero vector, v1 is already orthogonal
        return v1

    v1_parallel = (dot_product / norm_sq) * v2

    # The orthogonal component is v1 - v1_parallel
    return v1 - v1_parallel


def patch_to_mesh(patches):
    mesh = model.Mesh()

    for patch in patches:
        mesh.append(patch.tessellate())
    mesh.optimize()

    return mesh


def unpack_edges(edges):
    output = []
    for edge in edges:
        if len(edge) <= 2:
            output.append(edge)
        else:
            for i, a_key in enumerate(edge[:-1]):
                b_key = edge[i + 1]
                if [a_key, b_key] in output or [b_key, a_key] in output:
                    print(f'Multiple edge entries {a_key}:{b_key}')
                    raise KeyError()
                output.append([a_key, b_key])
    return output


def unpack_index(pair):
    return pair if isinstance(pair, int) else pair[0]


class BezierObject:
    class JointCorner:
        def __init__(self, center, points, unity_controls, tensions, resolution, inversion):
            self.center = center
            self.points = points
            self.unity_controls = unity_controls
            self.tensions = tensions
            self.resolution = resolution
            self.inversion = inversion

        def _build_quad(self):
            lines = make_quad_lines(self.points, self.unity_controls, self.tensions)
            patch = curves.BezierQuad(*lines, self.resolution, self.inversion)
            return [patch]

        def _build_quad_debug(self):
            lines = make_quad_lines(self.points, self.unity_controls, self.tensions)
            mesh = model.LineArray()

            mesh.geo_vertices.extend(sum(lines))
            mesh.geo_polygons.extend([[0, 1], [1, 2], [2, 3]])
            mesh.geo_polygons.extend([[4, 5], [5, 6], [6, 7]])
            mesh.geo_polygons.extend([[8, 9], [9, 10], [10, 11]])
            mesh.geo_polygons.extend([[12, 13], [13, 14], [14, 15]])
            mesh.geo_polygons.extend([[0, 4], [4, 8], [8, 12]])
            mesh.geo_polygons.extend([[1, 5], [5, 9], [9, 13]])
            mesh.geo_polygons.extend([[2, 6], [6, 10], [10, 14]])
            mesh.geo_polygons.extend([[3, 7], [7, 11], [11, 15]])

            return mesh

        def _build_tri(self):
            center = self.center - sum(control[0] for control in self.unity_controls) / 9.0
            vertices = make_tri_vertices(self.points, self.unity_controls, self.tensions)
            patch = curves.BezierTri(*vertices, center, self.resolution, self.inversion)
            return [patch]

        def _build_tri_debug(self):
            vertices = make_tri_vertices(self.points, self.unity_controls, self.tensions)
            mesh = model.LineArray()

            mesh.geo_vertices.extend([
                vertices[0][0],
                vertices[0][0] + vertices[0][2],
                vertices[0][0] + vertices[0][1]
            ])
            mesh.geo_vertices.extend([
                vertices[1][0],
                vertices[1][0] + vertices[1][1],
                vertices[1][0] + vertices[1][2]
            ])
            mesh.geo_vertices.extend([
                vertices[2][0],
                vertices[2][0] + vertices[2][2],
                vertices[2][0] + vertices[2][1]
            ])
            mesh.geo_vertices.append(self.center)
            mesh.geo_polygons.extend([[0, 1], [1, 4], [4, 3]])
            mesh.geo_polygons.extend([[0, 2], [2, 7], [7, 6]])
            mesh.geo_polygons.extend([[3, 5], [5, 8], [8, 6]])
            mesh.geo_polygons.extend([[1, 9], [2, 9], [4, 9], [5, 9], [7, 9], [8, 9]])

            return mesh

        def build(self):
            if len(self.points) == 4:
                return self._build_quad()
            return self._build_tri()

        def build_debug(self):
            if len(self.points) == 4:
                return self._build_quad_debug()
            return self._build_tri_debug()


    class JointEdge:
        TENSION = 1.0 / 3.0
        EPSILON = 1e-6

        def __init__(self, start, end, edge_resolution, line_resolution, inversion,
                     start_tension=None, end_tension=None):
            self.start = start
            self.end = end

            self.edge_resolution = edge_resolution
            self.line_resolution = line_resolution
            self.inversion = inversion

            self.beg_pos_m = self.start.position + self.start.u
            self.beg_pos_n = self.start.position + self.start.v
            self.beg_dir_m = -self.start.u * self.start.u_tension
            self.beg_dir_n = -self.start.v * self.start.v_tension

            self.end_pos_m = self.end.position + self.end.u
            self.end_pos_n = self.end.position + self.end.v
            self.end_dir_m = -self.end.u * self.end.u_tension
            self.end_dir_n = -self.end.v * self.end.v_tension

            self.direction = self.end.position - self.start.position
            product = np.linalg.det(np.array([self.beg_dir_m, self.beg_dir_n, self.direction]))
            if product > BezierObject.JointEdge.EPSILON:
                self.beg_dir_m, self.beg_dir_n = self.beg_dir_n, self.beg_dir_m
                self.beg_pos_m, self.beg_pos_n = self.beg_pos_n, self.beg_pos_m
            product = np.linalg.det(np.array([self.end_dir_m, self.end_dir_n, self.direction]))
            if product < -BezierObject.JointEdge.EPSILON:
                self.end_dir_m, self.end_dir_n = self.end_dir_n, self.end_dir_m
                self.end_pos_m, self.end_pos_n = self.end_pos_n, self.end_pos_m

            if start_tension is None:
                tension = BezierObject.JointEdge.TENSION
                self.beg_ten_m = (self.end_pos_n - self.beg_pos_m) * tension
                self.beg_ten_n = (self.end_pos_m - self.beg_pos_n) * tension
            else:
                self.beg_ten_m = self.beg_ten_n = start_tension

                product = np.linalg.det(np.array([self.direction, self.start.u, start_tension]))
                if abs(product) <= BezierObject.JointEdge.EPSILON:
                    scale = np.linalg.norm(self.end_pos_n - self.beg_pos_m) / np.linalg.norm(self.direction)
                    self.beg_ten_m = start_tension * scale
                product = np.linalg.det(np.array([self.direction, self.start.v, start_tension]))
                if abs(product) <= BezierObject.JointEdge.EPSILON:
                    scale = np.linalg.norm(self.end_pos_m - self.beg_pos_n) / np.linalg.norm(self.direction)
                    self.beg_ten_n = start_tension * scale

            if end_tension is None:
                tension = BezierObject.JointEdge.TENSION
                self.end_ten_m = (self.beg_pos_n - self.end_pos_m) * tension
                self.end_ten_n = (self.beg_pos_m - self.end_pos_n) * tension
            else:
                self.end_ten_m = self.end_ten_n = end_tension

                product = np.linalg.det(np.array([self.direction, self.end.u, end_tension]))
                if abs(product) <= BezierObject.JointEdge.EPSILON:
                    scale = np.linalg.norm(self.beg_pos_n - self.end_pos_m) / np.linalg.norm(self.direction)
                    self.end_ten_m = end_tension * scale
                product = np.linalg.det(np.array([self.direction, self.end.v, end_tension]))
                if abs(product) <= BezierObject.JointEdge.EPSILON:
                    scale = np.linalg.norm(self.beg_pos_m - self.end_pos_n) / np.linalg.norm(self.direction)
                    self.end_ten_n = end_tension * scale

        def get_tension_by_corner(self, point):
            corners = (self.beg_pos_m, self.beg_pos_n, self.end_pos_m, self.end_pos_n)
            tensions = (self.beg_ten_m, self.beg_ten_n, self.end_ten_m, self.end_ten_n)

            for i, corner in enumerate(corners):
                if model.Mesh.isclose(point, corner):
                    return tensions[i]
            return None

        def build(self):
            # TODO Triangular edges
            if self.start.singular or self.end.singular:
                raise ValueError()

            tension = BezierObject.JointEdge.TENSION
            beg_ten_mn = self.beg_ten_m + (self.end_dir_n - self.beg_dir_m) * tension
            beg_ten_nm = self.beg_ten_n + (self.end_dir_m - self.beg_dir_n) * tension
            end_ten_mn = self.end_ten_m + (self.beg_dir_n - self.end_dir_m) * tension
            end_ten_nm = self.end_ten_n + (self.beg_dir_m - self.end_dir_n) * tension

            line0 = (
                self.beg_pos_n,
                self.beg_pos_n + self.beg_dir_n,
                self.beg_pos_m + self.beg_dir_m,
                self.beg_pos_m
            )
            line3 = (
                self.end_pos_m,
                self.end_pos_m + self.end_dir_m,
                self.end_pos_n + self.end_dir_n,
                self.end_pos_n
            )
            line1 = (
                line0[0] + self.beg_ten_n,
                line0[1] + beg_ten_nm,
                line0[2] + beg_ten_mn,
                line0[3] + self.beg_ten_m
            )
            line2 = (
                line3[0] + self.end_ten_m,
                line3[1] + end_ten_mn,
                line3[2] + end_ten_nm,
                line3[3] + self.end_ten_n
            )

            patch = curves.BezierQuad(line0, line1, line2, line3,
                                      (self.edge_resolution, self.line_resolution), self.inversion)
            return [patch]


    class JointPatch:
        def __init__(self, points, tensions, resolution, inversion):
            self.points = points
            self.resolution = resolution
            self.tensions = tensions
            self.inversion = inversion
            self.functor = default_face_functor

        def build(self):
            if self.functor is not None:
                return self.functor(self.points, self.tensions, self.resolution, self.inversion)
            return None


    class JointVector:
        def __init__(self, position, singular, u=np.zeros(3), u_tension=np.zeros(3),
                     v=np.zeros(3), v_tension=np.zeros(3)):
            self.position = position
            self.singular = singular
            self.u = u
            self.v = v
            self.u_tension = u_tension
            self.v_tension = v_tension


    def __init__(self, vertices, edges, faces, chamfer, edge_resolution, line_resolution,
                 sharpness=math.pi, vertex_attributes=None, edge_attributes=None,
                 face_attributes=None):
        self.edges = unpack_edges(edges)
        self.graph = make_graph(self.edges)
        self.vertices = vertices
        self.faces = faces

        self.chamfer = chamfer
        self.sharpness = math.cos(sharpness)
        self.epsilon = 1e-6

        self.edge_resolution=edge_resolution
        self.line_resolution=line_resolution

        self.vertex_attributes = vertex_attributes if vertex_attributes is not None else {}
        self.edge_attributes = {}
        if edge_attributes is not None:
            for key, value in edge_attributes.items():
                refined_key = tuple(sorted(key))
                self.edge_attributes[refined_key] = value
        self.face_attributes = {}
        if face_attributes is not None:
            for key, value in face_attributes.items():
                refined_key = tuple(sorted(key))
                self.face_attributes[refined_key] = value

        self._build_joints()
        self._build_groups()

    @staticmethod
    def make_debug_frame(center, dirs, corner_pos, corner_control, corner_tension):
        debug_objects = {}

        debug_dir = model.LineArray()
        debug_dir.geo_vertices.extend([center] + [center + pos for pos in dirs])
        for i in range(len(dirs)):
            debug_dir.geo_polygons.append([0, 1 + i])
        debug_objects['dir'] = debug_dir

        debug_control = model.LineArray()
        debug_control.geo_vertices.extend([center] + [corner[1] for corner in corner_pos])
        debug_control.geo_polygons.extend([[0, 1 + i] for i in range(len(corner_pos))])
        c_index, v_index = 1, len(debug_control.geo_vertices)
        for i, control in enumerate(corner_control):
            pos = corner_pos[i][1]
            debug_control.geo_vertices.extend([pos + control[0],
                                               pos + control[1]])
            debug_control.geo_polygons.append([c_index + i, v_index + i * 2])
            debug_control.geo_polygons.append([c_index + i, v_index + i * 2 + 1])
        debug_objects['control'] = debug_control

        debug_tension = model.LineArray()
        debug_tension.geo_vertices.extend([center] + [corner[1] for corner in corner_pos])
        debug_tension.geo_polygons.extend([[0, 1 + i] for i in range(len(corner_pos))])
        c_index, v_index = 1, len(debug_tension.geo_vertices)
        for i, control in enumerate(corner_control):
            pos = corner_pos[i][1]
            debug_tension.geo_vertices.extend([pos + control[0] * corner_tension[i][0],
                                               pos + control[1] * corner_tension[i][1]])
            debug_tension.geo_polygons.append([c_index + i, v_index + i * 2])
            debug_tension.geo_polygons.append([c_index + i, v_index + i * 2 + 1])
        debug_objects['tension'] = debug_tension

        return debug_objects

    @staticmethod
    def index_range(a_key, b_key, length):
        output = []
        while True:
            a_key = (a_key + 1) % length
            if a_key != b_key:
                output.append(a_key)
            else:
                break
        return output

    @staticmethod
    def process_joint(center, neighbors, chamfers, sharpness, resolution, inversion, epsilon):
        vectors, keys = list(neighbors.values()), list(neighbors.keys())
        dirs = [model.normalize(vector - center) for vector in vectors]
        mean = model.normalize(sum(dirs))
        normal = model.normalize(sum(np.cross(dirs[i - 1], dirs[i]) for i in range(len(dirs))))

        if np.dot(normal, mean) < 0.0:
            vectors.reverse()
            keys.reverse()
            chamfers.reverse()

        dirs = [model.normalize(vector - center) for vector in vectors]
        triple_products = []
        for i in range(len(dirs)):
            a_key, b_key, c_key = i - 1, i, (i + 1) % len(dirs)
            product = np.linalg.det(np.array([dirs[a_key], dirs[b_key], dirs[c_key]]))
            triple_products.append(product)

        flattened = [bool(abs(value) <= epsilon) for value in triple_products]
        if all(flattened):
            # Special case without patch and edges
            output_corners = {key: center for key in keys}
            return (output_corners, {}, None, None)

        if flattened.count(False) > 4:
            print(f'Patch has too many corners: {flattened.count(False)}')
            raise ValueError()

        folded_pair = None
        if len(dirs) > 3:
            allowed_points = [i for i, value in enumerate(flattened) if not value]
            pairs = list(itertools.combinations(allowed_points, 2))
            pairs_folded = [bool(np.dot(dirs[i], dirs[j]) < sharpness) for i, j in pairs]
            folded_count = pairs_folded.count(True)
            if folded_count:
                if folded_count > 1:
                    print(f'Patch has too many folding diagonals: {folded_count}')
                    raise ValueError()
                folded_pair = pairs[pairs_folded.index(True)]

        corner_pos = []
        corner_control = []
        skipped_corner_map = {}

        if folded_pair is None:
            for i in range(len(dirs)):
                key, a_key, b_key = None, i, (i + 1) % len(dirs)
                average = np.zeros(3)

                if flattened[a_key]:
                    continue
                if flattened[b_key]:
                    key = b_key

                while b_key != a_key and flattened[b_key]:
                    average += dirs[b_key]
                    b_key = (b_key + 1) % len(dirs)
                average = model.normalize(average)

                if a_key == b_key:
                    print('Incorrect edge configuration')
                    raise ValueError()

                a_ortho = model.normalize(make_orthogonal(dirs[a_key], dirs[b_key]))
                a_ortho *= chamfers[b_key]
                b_ortho = model.normalize(make_orthogonal(dirs[b_key], dirs[a_key]))
                b_ortho *= chamfers[a_key]
                ab_cross_point = curves.get_closest_point(center + b_ortho, dirs[b_key],
                                                          center + a_ortho, dirs[a_key])

                ab_vector = ab_cross_point - center
                if key is not None and np.dot(ab_vector, average) < 0.0:
                    ab_vector = -ab_vector
                    ab_cross_point = ab_vector + center

                a_control_point = curves.get_closest_point(ab_cross_point, dirs[a_key],
                                                           center, dirs[b_key])
                b_control_point = curves.get_closest_point(ab_cross_point, dirs[b_key],
                                                           center, dirs[a_key])
                a_control = center - a_control_point
                b_control = center - b_control_point

                if key is not None and np.dot(np.cross(dirs[a_key], dirs[b_key]), mean) < 0.0:
                    a_control, b_control = b_control, a_control
                corner_control.append((a_control, b_control))

                skipped_corner_map.update({i: len(corner_pos)
                    for i in BezierObject.index_range(a_key, b_key, len(dirs))})
                corner_pos.append(((a_key, b_key, key), center + ab_vector, key is not None))
        else:
            a_key, b_key = folded_pair
            # Side left to the folding diagonal
            l_side = BezierObject.index_range(a_key, b_key, len(dirs))
            # Side right to the folding diagonal
            r_side = BezierObject.index_range(b_key, a_key, len(dirs))

            l_control = sum(dirs[i] * chamfers[i] for i in l_side) / len(l_side)
            r_control = sum(dirs[i] * chamfers[i] for i in r_side) / len(r_side)

            for i in l_side:
                for j in r_side:
                    corner_control.append((r_control, l_control))
                    corner_pos.append(((j, i, a_key), center, True))
                    corner_control.append((l_control, r_control))
                    corner_pos.append(((i, j, b_key), center, True))

        if folded_pair is not None:
            corner_tension = []
            for corner in corner_pos:
                a_key, b_key, _ = corner[0]
                angle = model.angle(dirs[a_key], dirs[b_key])
                tension = curves.calc_bezier_weight(angle=angle)
                corner_tension.append((tension, tension))

            if DEBUG_ENABLED:
                debug_objects = BezierObject.make_debug_frame(center, dirs, corner_pos,
                                                              corner_control, corner_tension)
            else:
                debug_objects = None

            output_corners, output_vectors = {}, {}
            for key in keys:
                for i, corner in enumerate(corner_pos):
                    if corner[0][2] is not None and key == keys[corner[0][2]]:
                        tangents = (
                            (corner_control[i][0], corner_tension[i][0]),
                            (corner_control[i][1], corner_tension[i][1])
                        )
                        output_vectors[key] = BezierObject.JointVector(corner[1], False,
                                                                       *tangents[0], *tangents[1])

                        pair_key = tuple(sorted((keys[corner[0][2]], keys[corner[0][0]])))
                        if pair_key not in output_corners:
                            output_corners[pair_key] = corner[1] + corner_control[i][0]
                        pair_key = tuple(sorted((keys[corner[0][2]], keys[corner[0][1]])))
                        if pair_key not in output_corners:
                            output_corners[pair_key] = corner[1] + corner_control[i][1]
                        break
                    if key == keys[corner[0][0]]:
                        origin = corner[1] + corner_control[i][0]
                        output_vectors[key] = BezierObject.JointVector(origin, True)
                        output_corners[key] = origin
                        break
                    if key == keys[corner[0][1]]:
                        origin = corner[1] + corner_control[i][1]
                        output_vectors[key] = BezierObject.JointVector(origin, True)
                        output_corners[key] = origin
                        break

            # Simplified case for flat diagonals
            return (output_corners, output_vectors, None, debug_objects)

        corner_control_update = []
        for b_key, b_control in enumerate(corner_control):
            a_key, c_key = b_key - 1, (b_key + 1) % len(corner_control)
            b_pos = corner_pos[b_key][1]

            if corner_pos[b_key][2]:
                a_pos = corner_pos[a_key][1] + corner_control[a_key][1]
                c_pos = corner_pos[c_key][1] + corner_control[c_key][0]
            else:
                a_pos = b_pos + b_control[0]
                if not corner_pos[a_key][2]:
                    a_pos = (a_pos + corner_pos[a_key][1] + corner_control[a_key][1]) / 2.0

                c_pos = b_pos + b_control[1]
                if not corner_pos[c_key][2]:
                    c_pos = (c_pos + corner_pos[c_key][1] + corner_control[c_key][0]) / 2.0

            a_control = a_pos - b_pos
            c_control = c_pos - b_pos
            corner_control_update.append((a_control, c_control))
        corner_control = corner_control_update

        corner_tension = []
        for b_key, b_control in enumerate(corner_control):
            a_key, c_key = b_key - 1, (b_key + 1) % len(corner_control)
            a_angle = model.angle(b_control[0], corner_control[a_key][1])
            c_angle = model.angle(b_control[1], corner_control[c_key][0])
            a_tension = curves.calc_bezier_weight(angle=a_angle)
            c_tension = curves.calc_bezier_weight(angle=c_angle)
            corner_tension.append((a_tension, c_tension))

        if DEBUG_ENABLED:
            debug_objects = BezierObject.make_debug_frame(center, dirs, corner_pos,
                                                          corner_control, corner_tension)
        else:
            debug_objects = None

        output_corners = {}
        output_vectors = {}
        output_patch = None

        for corner in corner_pos:
            pair_key = tuple(sorted((keys[corner[0][0]], keys[corner[0][1]])))
            if pair_key in output_corners:
                raise ValueError()
            output_corners[pair_key] = corner[1]
        for i, remap in skipped_corner_map.items():
            key = keys[i]
            if key in output_corners:
                raise ValueError()
            output_corners[key] = corner_pos[remap][1]

        for key in keys:
            origin = None
            tangents = []

            for i, corner in enumerate(corner_pos):
                if corner[0][2] is not None and key == keys[corner[0][2]]:
                    output_corners[key] = corner[1]
                    output_vectors[key] = BezierObject.JointVector(corner[1], True)
                    break

                if key == keys[corner[0][0]]:
                    if origin is None:
                        origin = corner[1] + corner_control[i][0]
                    tangents.append((-corner_control[i][0], corner_tension[i][0]))
                elif key == keys[corner[0][1]]:
                    if origin is None:
                        origin = corner[1] + corner_control[i][1]
                    tangents.append((-corner_control[i][1], corner_tension[i][1]))
            if origin is not None:
                output_vectors[key] = BezierObject.JointVector(origin, False,
                                                               *tangents[0], *tangents[1])

        if len(corner_pos) in (3, 4):
            output_patch = BezierObject.JointCorner(center, [corner[1] for corner in corner_pos],
                                                    corner_control, corner_tension,
                                                    resolution, inversion)

        return (output_corners, output_vectors, output_patch, debug_objects)

    def find_face(self, face):
        key = tuple(sorted(face))
        if key in self.output_faces:
            return self.output_faces[key]
        return None

    def get_edge_inversion(self, key):
        if not key in self.edge_attributes:
            return False

        attributes = self.edge_attributes[key]
        if 'inversion' in attributes:
            return attributes['inversion']
        return False

    def get_edge_resolution(self, key):
        if not key in self.edge_attributes:
            return self.line_resolution

        attributes = self.edge_attributes[key]
        if 'resolution' in attributes:
            return attributes['resolution']
        return self.line_resolution

    def get_face_inversion(self, key):
        if not key in self.face_attributes:
            return False

        attributes = self.face_attributes[key]
        if 'inversion' in attributes:
            return attributes['inversion']
        return False

    def get_face_resolution(self, numbers):
        pairs = [(current, numbers[(i + 1) % len(numbers)]) for i, current in enumerate(numbers)]
        resolutions = []
        for pair in pairs:
            key = tuple(sorted(pair))
            resolutions.append(self.get_edge_resolution(key))

        if len(numbers) == 4:
            if resolutions[0] != resolutions[2] or resolutions[1] != resolutions[3]:
                print(f'Face {numbers} resolutions not matched: {resolutions}')
                raise ValueError()
            return (resolutions[0], resolutions[1])
        if len(numbers) == 3:
            if resolutions[0] != resolutions[1] or resolutions[1] != resolutions[2]:
                print(f'Face {numbers} resolutions not matched: {resolutions}')
                raise ValueError()
            return resolutions[0]
        raise ValueError()

    def get_vertex_chamfer(self, source, destination):
        try:
            chamfer_info = self.vertex_attributes[source]['chamfer']
            if isinstance(chamfer_info, dict):
                return chamfer_info[destination]
            return chamfer_info
        except KeyError:
            return self.chamfer

    def get_vertex_inversion(self, key):
        if not key in self.vertex_attributes:
            return False

        attributes = self.vertex_attributes[key]
        if 'inversion' in attributes:
            return attributes['inversion']
        return False

    def get_vertex_resolution(self, *args):
        try:
            if len(args) > 1:
                resolutions = [self.vertex_attributes[key]['resolution'] for key in args]
                if resolutions.count(resolutions[0]) != len(resolutions):
                    print(f'Vertex {args} resolutions not matched: {resolutions}')
                    raise ValueError()
                return resolutions[0]
            return self.vertex_attributes[args[0]]['resolution']
        except KeyError:
            return self.edge_resolution

    def get_debug_output(self):
        if self.debug_objects is not None:
            return self.debug_objects

        return {
            'dir': model.LineArray(),
            'control': model.LineArray(),
            'tension': model.LineArray()
        }

    def get_joint_neighbor_position(self, source, destination):
        try:
            tension_info = self.vertex_attributes[source]['bezier']
            return self.vertices[source] + tension_info[destination]
        except KeyError:
            return self.vertices[destination]

    def get_joint_neighbor_tension(self, source, destination, nearest=None):
        if nearest is not None:
            try:
                key = tuple(sorted((source, destination)))
                edge = self.output_edges[key]
                tension = edge.get_tension_by_corner(nearest)
                if tension is not None:
                    return tension
            except KeyError:
                pass

        try:
            tension_info = self.vertex_attributes[source]['bezier']
            return tension_info[destination]
        except KeyError:
            return None

    def is_edge_hidden(self, key):
        if not key in self.edge_attributes:
            return False

        attributes = self.edge_attributes[key]
        if 'hidden' in attributes:
            return attributes['hidden']
        return False

    def is_vertex_discarded(self, key):
        if not key in self.vertex_attributes:
            return False

        attributes = self.vertex_attributes[key]
        if 'discard' in attributes:
            return attributes['discard']
        return False

    def is_vertex_hidden(self, key):
        if not key in self.vertex_attributes:
            return False

        attributes = self.vertex_attributes[key]
        if 'hidden' in attributes:
            return attributes['hidden']
        return False

    def _build_joints(self):
        self.debug_objects = None
        self.joint_corners = {}
        self.joint_vectors = {}
        self.output_vertices = {}

        # Append corners with three neighbors
        joint_points = {key: value for key, value in self.graph.items() if len(value) == 3}
        # Append corners with four or more neighbors
        for number in [key for key, value in self.graph.items() if len(value) > 3]:
            graph_copy = copy.deepcopy(self.graph)
            points = graph_copy[number]
            del graph_copy[number]

            sequences = []
            for sequence in itertools.permutations(points, len(points)):
                chunks = []
                for i, current in enumerate(sequence):
                    previous = sequence[i - 1]
                    chunks.append(find_shortest_path(graph_copy, previous, current))
                sequences.append((sequence, sum(len(chunk) for chunk in chunks)))
                shortest_sequence = min(sequences, key=lambda item: item[1])
                joint_points[number] = shortest_sequence[0]

        # Calculate corner positions and tangent vectors, calculate corner patches
        for number, sequence in joint_points.items():
            if self.is_vertex_discarded(number):
                continue

            joint_chamfers = [self.get_vertex_chamfer(number, i) for i in sequence]
            joint_inversion = self.get_vertex_inversion(number)
            joint_neighbors = {i: self.get_joint_neighbor_position(number, i) for i in sequence}
            joint_resolution = self.get_vertex_resolution(number)

            corners, edges, patch, debug = BezierObject.process_joint(
                self.vertices[number],
                joint_neighbors,
                joint_chamfers,
                self.sharpness,
                joint_resolution,
                joint_inversion,
                self.epsilon
            )

            if debug is not None:
                if self.debug_objects is None:
                    self.debug_objects = debug
                else:
                    self.debug_objects['dir'].append(debug['dir'])
                    self.debug_objects['control'].append(debug['control'])
                    self.debug_objects['tension'].append(debug['tension'])

            if corners:
                self.joint_corners[number] = corners
            if edges:
                self.joint_vectors[number] = edges
            if patch is not None and not self.is_vertex_hidden(number):
                self.output_vertices[number] = patch

    def _build_groups(self):
        self.output_edges = {}
        self.output_faces = {}

        for start, end in self.edges:
            if start in self.joint_vectors and end in self.joint_vectors:
                if end in self.joint_vectors[start] and start in self.joint_vectors[end]:
                    a = self.joint_vectors[start][end]
                    b = self.joint_vectors[end][start]
                    if not a.singular and not b.singular:
                        key = tuple(sorted((start, end)))
                        if self.is_edge_hidden(key):
                            continue

                        edge_inversion = self.get_edge_inversion(key)
                        joint_resolution = self.get_vertex_resolution(*key)
                        line_resolution = self.get_edge_resolution(key)

                        edge_a_tension = self.get_joint_neighbor_tension(start, end)
                        edge_b_tension = self.get_joint_neighbor_tension(end, start)

                        self.output_edges[key] = BezierObject.JointEdge(
                            a, b,
                            joint_resolution, line_resolution,
                            edge_inversion,
                            edge_a_tension, edge_b_tension
                        )

        for face in self.faces:
            indices = face[::-1]
            points = []
            tensions = []

            for i, b_index in enumerate(indices):
                a_index, c_index = indices[i - 1], indices[(i + 1) % len(indices)]
                point = None

                # Indices may be tuples used as fake edge keys where first part is the real index
                # and second part is the fake corner index
                a_key = unpack_index(a_index)
                b_key = unpack_index(b_index)
                c_key = unpack_index(c_index)

                if b_key in self.joint_corners:
                    corners = self.joint_corners[b_key]
                    a_corner_key = a_key if isinstance(a_index, int) else tuple(sorted(a_index))
                    c_corner_key = c_key if isinstance(c_index, int) else tuple(sorted(c_index))

                    if c_corner_key in corners:
                        point = corners[c_corner_key]
                    elif a_corner_key in corners:
                        point = corners[a_corner_key]
                    elif isinstance(a_index, int) and isinstance(c_index, int):
                        corner_key = tuple(sorted((a_key, c_key)))
                        if corner_key in corners:
                            point = corners[corner_key]

                if point is None:
                    print(f'Point {b_key} in face {face} not found')
                    raise KeyError()
                points.append(point)

                tension_a = self.get_joint_neighbor_tension(b_key, a_key, point)
                tension_c = self.get_joint_neighbor_tension(b_key, c_key, point)
                tensions.append((tension_a, tension_c))

            if len(points) != len(indices):
                print(f'Not enough points for face {face} found: {len(points)}')
                raise KeyError()

            face_key = tuple(sorted((unpack_index(part) for part in indices)))
            patch_inversion = self.get_face_inversion(face_key)
            patch_resolution = self.get_face_resolution([unpack_index(part) for part in indices])

            self.output_faces[face_key] = BezierObject.JointPatch(
                points,
                tensions,
                patch_resolution,
                patch_inversion
            )

    def build(self):
        output = []
        for vertex in self.output_vertices.values():
            output.extend(vertex.build())
        for edge in self.output_edges.values():
            patches = edge.build()
            if patches is not None:
                output.extend(patches)
        for face in self.output_faces.values():
            patches = face.build()
            if patches is not None:
                output.extend(patches)
        return output


def debug_vertex_controls(vertices, vertex_attributes):
    mesh = model.LineArray()
    for i, vertex in enumerate(vertices):
        try:
            controls = vertex_attributes[i]['bezier']
        except KeyError:
            continue

        if not controls:
            print(f'Empty description for vertex {i}')
            raise KeyError()

        last = len(mesh.geo_vertices)
        mesh.geo_vertices.append(vertex)
        for key, value in controls.items():
            if key >= len(vertices):
                print(f'Incorrect vertex number {key}')
                raise ValueError()
            mesh.geo_polygons.append([last, len(mesh.geo_vertices)])
            mesh.geo_vertices.append(vertex + value)
    return mesh


def debug_edges(vertices, edges, vertex_attributes=None):
    mesh = model.LineArray()
    mesh.geo_vertices.extend(vertices)
    edges = unpack_edges(edges)
    for edge in edges:
        if vertex_attributes is not None:
            try:
                control_beg = vertex_attributes[edge[0]]['bezier'][edge[1]]
                control_end = vertex_attributes[edge[1]]['bezier'][edge[0]]
                curve = curves.Bezier(vertices[edge[0]], control_beg,
                                    vertices[edge[1]], control_end, 10)
                curve_points = curve.tessellate()
                start_index = len(mesh.geo_vertices)
                mesh.geo_vertices.extend(curve_points[1:-1])
                for i in range(0, len(curve_points) - 1):
                    edge_start, edge_end = start_index + i - 1, start_index + i
                    if i == 0:
                        edge_start = edge[0]
                    elif i == len(curve_points) - 2:
                        edge_end = edge[1]
                    mesh.geo_polygons.append([edge_start, edge_end])
                continue
            except KeyError:
                pass
        mesh.geo_polygons.append(edge)
    return mesh


def debug_face_polygons(vertices, faces):
    mesh = model.Mesh()
    mesh.geo_vertices.extend(vertices)
    mesh.geo_polygons.extend(faces)
    return mesh


def debug_face_normals(vertices, faces):
    mesh = model.LineArray()
    for indices in faces:
        normal = model.normalize(np.cross(vertices[indices[1]] - vertices[indices[0]],
                                          vertices[indices[2]] - vertices[indices[0]]))
        center = sum(vertices[i] for i in indices) / len(indices)
        start = len(mesh.geo_vertices)
        mesh.geo_vertices.extend([center, center + normal])
        mesh.geo_polygons.append([start, start + 1])
    return mesh
