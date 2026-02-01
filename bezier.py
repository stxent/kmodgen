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

def make_quad_lines(points, controls, tensions):
    control_points = (
        (
            points[0],
            controls[0][1] * tensions[0][1],
            controls[0][0] * tensions[0][0]
        ), (
            points[1],
            controls[1][1] * tensions[1][1],
            controls[1][0] * tensions[1][0]
        ), (
            points[2],
            controls[2][1] * tensions[2][1],
            controls[2][0] * tensions[2][0]
        ), (
            points[3],
            controls[3][1] * tensions[3][1],
            controls[3][0] * tensions[3][0]
        )
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

def make_tri_vertices(points, controls, tensions):
    control_points = ((
            points[0],
            controls[0][0] * tensions[0][0],
            controls[0][1] * tensions[0][1]
        ), (
            points[1],
            controls[1][0] * tensions[1][0],
            controls[1][1] * tensions[1][1]
        ), (
            points[2],
            controls[2][0] * tensions[2][0],
            controls[2][1] * tensions[2][1]
        )
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
        lines = make_quad_lines(points, output_controls, [np.ones(2)] * 4)
        return curves.BezierQuad(*lines, resolution, inversion)
    if len(points) == 3:
        mean = sum(points) / 3.0
        center = mean
        # center = mean - sum(control[0] for controls) * (8.0 / 9.0) # XXX
        lines = make_tri_vertices(points, output_controls, [np.ones(2)] * 3)
        return curves.BezierTri(*lines, center, resolution, inversion)
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


class BezierObject:
    class JointCorner:
        def __init__(self, center, points, unity_controls, tensions, resolution, inversion):
            self.center = center
            self.points = points
            self.unity_controls = unity_controls
            self.tensions = tensions
            self.resolution = resolution
            self.inversion = inversion

        def _tesselate_quad(self):
            lines = make_quad_lines(self.points, self.unity_controls, self.tensions)
            return curves.BezierQuad(*lines, self.resolution, self.inversion)

        def _tesselate_quad_debug(self):
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

        def _tesselate_tri(self):
            center = self.center - sum(control[0] for control in self.unity_controls) / 9.0
            vertices = make_tri_vertices(self.points, self.unity_controls, self.tensions)
            return curves.BezierTri(*vertices, center, self.resolution, self.inversion)

        def _tesselate_tri_debug(self):
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

        def tessellate(self):
            if len(self.points) == 4:
                return self._tesselate_quad()
            return self._tesselate_tri()

        def tessellate_debug(self):
            if len(self.points) == 4:
                return self._tesselate_quad_debug()
            return self._tesselate_tri_debug()


    class JointEdge:
        DEFAULT_TENSION = 1.0 / 3.0

        def __init__(self, start, end, edge_resolution, line_resolution, inversion,
                     start_tension=None, end_tension=None):
            self.start = start
            self.start_tension = start_tension
            self.end = end
            self.end_tension = end_tension

            self.edge_resolution = edge_resolution
            self.line_resolution = line_resolution
            self.inversion = inversion

        def tessellate(self):
            # TODO Triangular edges
            if self.start.singular or self.end.singular:
                raise ValueError()

            beg_pos_m = self.start.position + self.start.u
            beg_pos_n = self.start.position + self.start.v
            beg_dir_m = -self.start.u * self.start.u_tension
            beg_dir_n = -self.start.v * self.start.v_tension

            end_pos_m = self.end.position + self.end.u
            end_pos_n = self.end.position + self.end.v
            end_dir_m = -self.end.u * self.end.u_tension
            end_dir_n = -self.end.v * self.end.v_tension

            direction = (end_pos_m + end_pos_n) - (beg_pos_m + beg_pos_n)
            if np.linalg.det(np.array([beg_dir_m, beg_dir_n, direction])) > 0.0:
                beg_dir_m, beg_dir_n = beg_dir_n, beg_dir_m
                beg_pos_m, beg_pos_n = beg_pos_n, beg_pos_m
            if np.linalg.det(np.array([end_dir_m, end_dir_n, direction])) < 0.0:
                end_dir_m, end_dir_n = end_dir_n, end_dir_m
                end_pos_m, end_pos_n = end_pos_n, end_pos_m

            line0 = (
                beg_pos_n,
                beg_pos_n + beg_dir_n,
                beg_pos_m + beg_dir_m,
                beg_pos_m
            )
            line3 = (
                end_pos_m,
                end_pos_m + end_dir_m,
                end_pos_n + end_dir_n,
                end_pos_n
            )

            if self.start_tension is None:
                line1 = (
                    line0[0] + (line3[0] - line0[0]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line0[1] + (line3[1] - line0[1]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line0[2] + (line3[2] - line0[2]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line0[3] + (line3[3] - line0[3]) * BezierObject.JointEdge.DEFAULT_TENSION
                )
            else:
                line1 = (
                    line0[0] + self.start_tension,
                    line0[1] + self.start_tension,
                    line0[2] + self.start_tension,
                    line0[3] + self.start_tension
                )

            if self.end_tension is None:
                line2 = (
                    line3[0] + (line0[0] - line3[0]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line3[1] + (line0[1] - line3[1]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line3[2] + (line0[2] - line3[2]) * BezierObject.JointEdge.DEFAULT_TENSION,
                    line3[3] + (line0[3] - line3[3]) * BezierObject.JointEdge.DEFAULT_TENSION
                )
            else:
                line2 = (
                    line3[0] + self.end_tension,
                    line3[1] + self.end_tension,
                    line3[2] + self.end_tension,
                    line3[3] + self.end_tension
                )

            return curves.BezierQuad(line0, line1, line2, line3,
                                     (self.line_resolution, self.edge_resolution), self.inversion)


    class JointPatch:
        def __init__(self, points, tensions, resolution, inversion):
            self.points = points
            self.resolution = resolution
            self.tensions = tensions
            self.inversion = inversion
            self.functor = default_face_functor

        def tessellate(self):
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
                 sharpness=math.pi, vertex_attributes={}, edge_attributes={}, face_attributes={}):
        self.edges = unpack_edges(edges)
        self.graph = make_graph(self.edges)
        self.vertices = vertices
        self.faces = faces

        self.chamfer = chamfer
        self.sharpness = math.cos(sharpness)
        self.epsilon = 1e-6

        self.edge_resolution=edge_resolution
        self.line_resolution=line_resolution

        self.vertex_attributes = vertex_attributes
        self.edge_attributes = {}
        for key, value in edge_attributes.items():
            refined_key = tuple(sorted(key))
            self.edge_attributes[refined_key] = value
        self.face_attributes = {}
        for key, value in face_attributes.items():
            refined_key = tuple(sorted(key))
            self.face_attributes[refined_key] = value

        self.build()
        self.build_objects()

    @staticmethod
    def make_debug_frame(center, dirs, corner_pos, corner_control, corner_tension):
        debug_objects = {}

        debug_dir = model.LineArray()
        debug_dir.geo_vertices.extend([center] + [center + pos for pos in dirs])
        for i in range(0, len(dirs)):
            debug_dir.geo_polygons.append([0, 1 + i])
        debug_objects['dir'] = debug_dir

        debug_control = model.LineArray()
        debug_control.geo_vertices.extend([center] + [corner[1] for corner in corner_pos])
        debug_control.geo_polygons.extend([[0, 1 + i] for i in range(0, len(corner_pos))])
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
        debug_tension.geo_polygons.extend([[0, 1 + i] for i in range(0, len(corner_pos))])
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
        normal = model.normalize(sum(np.cross(dirs[i - 1], dirs[i]) for i in range(0, len(dirs))))

        if np.dot(normal, mean) < 0.0:
            vectors.reverse()
            keys.reverse()
            chamfers.reverse()

        dirs = [model.normalize(vector - center) for vector in vectors]
        triple_products = []
        for i in range(0, len(dirs)):
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
            for i in range(0, len(dirs)):
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

            # if True:
            if False:
                l_average = model.normalize(sum(dirs[i] for i in l_side))
                r_average = model.normalize(sum(dirs[i] for i in r_side))
                l_chamfer = sum(chamfers[i] for i in l_side) / len(l_side)
                r_chamfer = sum(chamfers[i] for i in r_side) / len(r_side)
                l_control = l_average * l_chamfer
                r_control = r_average * r_chamfer
            else:
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

                        pair_key = tuple(sorted((keys[corner[0][2]], corner[0][0])))
                        if pair_key not in output_corners:
                            output_corners[pair_key] = corner[1] + corner_control[i][0]
                        pair_key = tuple(sorted((keys[corner[0][2]], corner[0][1])))
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

    def find_edge(self, start, end):
        key = tuple(sorted((start, end)))
        try:
            return self.output_edges[key]
        except KeyError:
            return None

    def find_face(self, face):
        key = tuple(sorted(face))
        try:
            return self.output_faces[key]
        except KeyError:
            return None

    def get_edge_inversion(self, key):
        try:
            return self.edge_attributes[key]['inversion']
        except KeyError:
            return False

    def get_edge_resolution(self, key):
        try:
            return self.edge_attributes[key]['resolution']
        except KeyError:
            return self.line_resolution

    def get_face_inversion(self, key):
        try:
            return self.face_attributes[key]['inversion']
        except KeyError:
            return False

    def get_face_resolution(self, numbers):
        pairs = [(numbers[i - 1], current) for i, current in enumerate(numbers)]
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
        try:
            return self.vertex_attributes[key]['inversion']
        except KeyError:
            return False

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

    def get_joint_neighbor_tension(self, source, destination):
        try:
            tension_info = self.vertex_attributes[source]['bezier']
            return tension_info[destination]
        except KeyError:
            return None

    def is_vertex_discarded(self, key):
        try:
            return self.vertex_attributes[key]['discard']
        except KeyError:
            return False

    def build(self):
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

            corners, edges, patch, debug = BezierObject.process_joint(
                self.vertices[number],
                joint_neighbors,
                joint_chamfers,
                self.sharpness,
                self.edge_resolution,
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
            if patch is not None:
                self.output_vertices[number] = patch

    def build_objects(self):
        self.output_edges = {}
        self.output_faces = {}

        for start, end in self.edges:
            if start in self.joint_vectors and end in self.joint_vectors:
                if end in self.joint_vectors[start] and start in self.joint_vectors[end]:
                    a = self.joint_vectors[start][end]
                    b = self.joint_vectors[end][start]
                    if not a.singular and not b.singular:
                        key = tuple(sorted((start, end)))
                        edge_inversion = self.get_edge_inversion(key)
                        edge_resolution = self.get_edge_resolution(key)

                        edge_a_tension = self.get_joint_neighbor_tension(start, end)
                        edge_b_tension = self.get_joint_neighbor_tension(end, start)

                        self.output_edges[key] = BezierObject.JointEdge(
                            a, b,
                            self.edge_resolution, edge_resolution,
                            edge_inversion,
                            edge_a_tension, edge_b_tension
                        )

        for face in self.faces:
            indices = face[::-1]
            points = []
            tensions = []

            for i, b_key in enumerate(indices):
                a_key, c_key = indices[i - 1], indices[(i + 1) % len(indices)]
                point = None
                tension_a = self.get_joint_neighbor_tension(b_key, a_key)
                tension_c = self.get_joint_neighbor_tension(b_key, c_key)

                if b_key in self.joint_corners:
                    corners = self.joint_corners[b_key]
                    if c_key in corners:
                        point = corners[c_key]
                    elif a_key in corners:
                        point = corners[a_key]
                    else:
                        corner_key = tuple(sorted((a_key, c_key)))
                        if corner_key in corners:
                            point = corners[corner_key]

                if point is None:
                    print(f'Point {b_key} in face {face} not found')
                    raise KeyError()
                points.append(point)
                tensions.append((tension_a, tension_c))

            if len(points) != len(indices):
                print(f'Not enough points for face {face} found: {len(points)}')
                raise KeyError()

            face_key = tuple(sorted(indices))
            patch_inversion = self.get_face_inversion(key)
            patch_resolution = self.get_face_resolution(indices)

            self.output_faces[face_key] = BezierObject.JointPatch(
                points,
                tensions,
                patch_resolution,
                patch_inversion
            )

    def tessellate(self):
        meshes = []

        for vertex in self.output_vertices.values():
            part = vertex.tessellate()
            meshes.append(part)

        for edge in self.output_edges.values():
            part = edge.tessellate()
            if part is not None:
                meshes.append(part)

        for face in self.output_faces.values():
            part = face.tessellate()
            if part is not None:
                meshes.append(part)

        mesh = model.Mesh()
        for part in meshes:
            mesh.append(part)
        mesh.optimize()

        return mesh


def debug_vertex_controls(vertices, vertex_attributes):
    mesh = model.LineArray()
    for i, vertex in enumerate(vertices):
        try:
            controls = vertex_attributes[i]['bezier']
        except:
            continue

        if not controls:
            print(f'Empty description for vertex {i}')
            raise KeyError()

        last = len(mesh.geo_vertices)
        mesh.geo_vertices.append(vertices[i])
        for key, value in controls.items():
            if key >= len(vertices):
                print(f'Incorrect vertex number {key}')
                raise ValueError()
            mesh.geo_polygons.append([last, len(mesh.geo_vertices)])
            mesh.geo_vertices.append(vertices[i] + value)
    return mesh

def debug_edges(vertices, edges):
    mesh = model.LineArray()
    mesh.geo_vertices.extend(vertices)
    mesh.geo_polygons.extend(unpack_edges(edges))
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
