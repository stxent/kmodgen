#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# crystals.py
# Copyright (C) 2026 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy as np

import bezier
import primitives
from packages import generic
from wrlconv import curves


class CrystalMetalCapSMD:
    DEFAULT_CHAMFER = primitives.hmils(0.05)
    BAND_SIZE = primitives.hmils(0.1)

    def __init__(self):
        pass

    @staticmethod
    def make_crystal_parts(body_size, body_cavity, body_chamfer,
                           contact_count, contact_height, contact_offset, contact_size,
                           bond_height, bond_offset, bond_width,
                           lid_chamfer, lid_height, lid_roundness,
                           arc_resolution, edge_resolution, line_resolution, plane_resolution):
        xy_body = np.array(body_size[:2]) / 2.0
        z_body = body_size[2] - lid_height - bond_height

        bond_tension = bond_width * curves.calc_bezier_weight(angle=math.pi / 2.0)
        xy_bond_outer = xy_body - bond_offset
        xy_bond_inner = xy_body - bond_offset - bond_width
        z_bond = body_size[2] - lid_height

        xy_lid = xy_body - bond_offset - bond_width - lid_chamfer * 2.0
        z_lid = body_size[2]

        def make_vertices(xy_position, z, r): # pylint: disable=invalid-name
            x, y = xy_position[0], xy_position[1]
            return [
                np.array([ x - r,      y, z]),
                np.array([     x,  y - r, z]),
                np.array([     x, -y + r, z]),
                np.array([ x - r,     -y, z]),
                np.array([-x + r,     -y, z]),
                np.array([    -x, -y + r, z]),
                np.array([    -x,  y - r, z]),
                np.array([-x + r,      y, z])
            ]

        def make_bot_edges(faces, resolution):
            attributes = {}
            edges = bezier.unpack_faces(faces)
            for edge in edges:
                attributes[tuple(edge)] = {bezier.RESOLUTION: resolution}
            return (edges, attributes)

        def make_bot_vertices_2(corner_offset, z, r, pad_offset, pad_size): # pylint: disable=invalid-name
            def mirror(vertices):
                return [np.array([-vertex[0], -vertex[1], vertex[2]]) for vertex in vertices]

            # Vertical pad size is ignored
            pad_x, pad_y = pad_size[0] / 2.0, corner_offset[1] - pad_offset
            pad_position = np.array([corner_offset[0] - pad_offset - pad_x, 0.0, 0.0])
            vertices = [
                pad_position + np.array([pad_x - r,      pad_y, z]),
                pad_position + np.array([    pad_x,  pad_y - r, z]),
                pad_position + np.array([    pad_x, -pad_y + r, z]),
                pad_position + np.array([pad_x - r,     -pad_y, z]),
                pad_position + np.array([   -pad_x,     -pad_y, z]),
                pad_position + np.array([   -pad_x,      pad_y, z])
            ]
            return vertices + mirror(vertices)

        def make_bot_faces_2(n, border_n): # pylint: disable=invalid-name
            body_faces = []
            body_attributes = {}
            lead_faces = []
            lead_attributes = {}

            for i in range(2):
                for j in range(2):
                    indices = [
                        n + i * 6 + j * 2,
                        border_n + i * 4 + j * 2,
                        border_n + i * 4 + j * 2 + 1,
                        n + i * 6 + j * 2 + 1
                    ]
                    lead_faces.append(indices)
                    lead_attributes[tuple(sorted(indices))] = {
                        bezier.FUNCTOR: primitives.asymmetric_face_functor
                    }
                lead_faces.append(list(range(n + i * 6, n + i * 6 + 4)))
                lead_faces.append([n + i * 6 + j for j in (0, 3, 4, 5)])

            body_faces.append([n + 4, n + 11, n + 10, n + 5])

            face_group_asymmetric = [
                [n + 5, border_n + 0, n + 0], [n + 3, border_n + 3, n + 4],
                [n + 11, border_n + 4, n + 6], [n + 9, border_n + 7, n + 10],

                [n + 1, border_n + 1, border_n + 2, n + 2],
                [n + 7, border_n + 5, border_n + 6, n + 8],
                [n + 10, border_n + 7, border_n + 0, n + 5],
                [n + 4, border_n + 3, border_n + 4, n + 11]
            ]

            for indices in face_group_asymmetric:
                body_faces.append(indices)
                body_attributes[tuple(sorted(indices))] = {
                    bezier.FUNCTOR: primitives.asymmetric_face_functor
                }

            return (body_faces, body_attributes, lead_faces, lead_attributes)

        def make_bot_vertices_4(corner_offset, z, r, pad_offset, pad_size): # pylint: disable=invalid-name
            def mirror_x(vertices):
                return [np.array([-vertex[0], vertex[1], vertex[2]]) for vertex in vertices]
            def mirror_y(vertices):
                return [np.array([vertex[0], -vertex[1], vertex[2]]) for vertex in vertices]

            pad_x, pad_y = pad_size[0] / 2.0, pad_size[1] / 2.0
            pad_position = corner_offset - pad_offset - np.array([pad_x, pad_y])
            pad_position = np.array([pad_position[0], pad_position[1], 0.0])
            vertices = [
                pad_position + np.array([pad_x - r,     pad_y, z]),
                pad_position + np.array([    pad_x, pad_y - r, z]),
                pad_position + np.array([    pad_x,    -pad_y, z]),
                pad_position + np.array([   -pad_x,    -pad_y, z]),
                pad_position + np.array([   -pad_x,     pad_y, z])
            ]
            return vertices + mirror_y(vertices) + mirror_x(mirror_y(vertices)) + mirror_x(vertices)

        def make_bot_faces_4(n, border_n): # pylint: disable=invalid-name
            body_faces = []
            body_attributes = {}
            lead_faces = []
            lead_attributes = {}

            for i in range(4):
                is_mirror_x, is_mirror_y = i in (2, 3), i in (1, 2)

                if is_mirror_x == is_mirror_y:
                    indices = [n + i * 5, border_n + i * 2, border_n + i * 2 + 1, n + i * 5 + 1]
                    lead_faces.append(indices)
                    lead_attributes[tuple(sorted(indices))] = {
                        bezier.FUNCTOR: primitives.asymmetric_face_functor
                    }

                    lead_faces.append([n + i * 5 + j for j in (4, 0, 1, 2)])
                    lead_faces.append([n + i * 5 + j for j in (2, 3, 4)])
                else:
                    indices = [n + i * 5 + 1, border_n + i * 2, border_n + i * 2 + 1, n + i * 5]
                    lead_faces.append(indices)
                    lead_attributes[tuple(sorted(indices))] = {
                        bezier.FUNCTOR: primitives.asymmetric_face_functor
                    }

                    lead_faces.append([n + i * 5 + j for j in (2, 1, 0, 4)])
                    lead_faces.append([n + i * 5 + j for j in (4, 3, 2)])

            body_faces.append([n + i * 5 + 3 for i in range(4)])
            body_faces.extend([
                [n + 0 * 5 + 2, n + 1 * 5 + 2, n + 1 * 5 + 3, n + 0 * 5 + 3],
                [n + 2 * 5 + 2, n + 3 * 5 + 2, n + 3 * 5 + 3, n + 2 * 5 + 3],
                [n + 0 * 5 + 3, n + 3 * 5 + 3, n + 3 * 5 + 4, n + 0 * 5 + 4],
                [n + 1 * 5 + 4, n + 2 * 5 + 4, n + 2 * 5 + 3, n + 1 * 5 + 3]
            ])

            face_group_asymmetric = [
                [n + 1, border_n + 1, n + 2], [n + 7, border_n + 2, n + 6],
                [n + 5, border_n + 3, n + 9], [n + 14, border_n + 4, n + 10],
                [n + 11, border_n + 5, n + 12], [n + 17, border_n + 6, n + 16],
                [n + 15, border_n + 7, n + 19], [n + 4, border_n + 0, n + 0],

                [n + 2, border_n + 1, border_n + 2, n + 7],
                [n + 9, border_n + 3, border_n + 4, n + 14],
                [n + 12, border_n + 5, border_n + 6, n + 17],
                [n + 19, border_n + 7, border_n + 0, n + 4]
            ]

            for indices in face_group_asymmetric:
                body_faces.append(indices)
                body_attributes[tuple(sorted(indices))] = {
                    bezier.FUNCTOR: primitives.asymmetric_face_functor
                }

            return (body_faces, body_attributes, lead_faces, lead_attributes)

        def make_top_vertices(xy_position, z, r): # pylint: disable=invalid-name
            x, y = xy_position[0], xy_position[1]
            return [
                np.array([ x - r,  y - r, z]),
                np.array([ x - r, -y + r, z]),
                np.array([-x + r, -y + r, z]),
                np.array([-x + r,  y - r, z])
            ]

        def make_controls(r, n): # pylint: disable=invalid-name
            w = abs(r) * curves.calc_bezier_weight(angle=math.pi / 2.0)

            if r < 0.0:
                return {
                    n + 1: {bezier.TENSION: {n + 0: np.array([ -w, 0.0, 0.0])}},
                    n + 0: {bezier.TENSION: {n + 1: np.array([0.0,  -w, 0.0])}},
                    n + 3: {bezier.TENSION: {n + 2: np.array([0.0,   w, 0.0])}},
                    n + 2: {bezier.TENSION: {n + 3: np.array([ -w, 0.0, 0.0])}},
                    n + 5: {bezier.TENSION: {n + 4: np.array([  w, 0.0, 0.0])}},
                    n + 4: {bezier.TENSION: {n + 5: np.array([0.0,   w, 0.0])}},
                    n + 7: {bezier.TENSION: {n + 6: np.array([0.0,  -w, 0.0])}},
                    n + 6: {bezier.TENSION: {n + 7: np.array([  w, 0.0, 0.0])}},
                }
            else:
                return {
                    n + 0: {bezier.TENSION: {n + 1: np.array([  w, 0.0, 0.0])}},
                    n + 1: {bezier.TENSION: {n + 0: np.array([0.0,   w, 0.0])}},
                    n + 2: {bezier.TENSION: {n + 3: np.array([0.0,  -w, 0.0])}},
                    n + 3: {bezier.TENSION: {n + 2: np.array([  w, 0.0, 0.0])}},
                    n + 4: {bezier.TENSION: {n + 5: np.array([ -w, 0.0, 0.0])}},
                    n + 5: {bezier.TENSION: {n + 4: np.array([0.0,  -w, 0.0])}},
                    n + 6: {bezier.TENSION: {n + 7: np.array([0.0,   w, 0.0])}},
                    n + 7: {bezier.TENSION: {n + 6: np.array([ -w, 0.0, 0.0])}},
                }

        def make_axial_controls(r, t, n): # pylint: disable=invalid-name
            linear_group = make_controls(r, n)
            for i in range(8):
                linear_group[n + i][bezier.TENSION][n - 8 + i] = np.array([0.0, 0.0, t])
            return linear_group

        def make_radial_controls(r, t, n): # pylint: disable=invalid-name
            linear_group = make_controls(r, n)
            linear_group[n + 1][bezier.TENSION][n +  9] = np.array([ -t, 0.0, 0.0])
            linear_group[n + 2][bezier.TENSION][n + 10] = np.array([ -t, 0.0, 0.0])
            linear_group[n + 3][bezier.TENSION][n + 11] = np.array([0.0,   t, 0.0])
            linear_group[n + 4][bezier.TENSION][n + 12] = np.array([0.0,   t, 0.0])
            linear_group[n + 5][bezier.TENSION][n + 13] = np.array([  t, 0.0, 0.0])
            linear_group[n + 6][bezier.TENSION][n + 14] = np.array([  t, 0.0, 0.0])
            linear_group[n + 7][bezier.TENSION][n + 15] = np.array([0.0,  -t, 0.0])
            linear_group[n + 0][bezier.TENSION][n +  8] = np.array([0.0,  -t, 0.0])
            return linear_group

        vertices = []
        vertex_attributes = {}

        if contact_count == 4:
            vertices.extend(make_bot_vertices_4(xy_body, 0.0, body_cavity,
                                                contact_offset, contact_size))
        else:
            vertices.extend(make_bot_vertices_2(xy_body, 0.0, body_cavity,
                                                contact_offset, contact_size))

        bot_n = len(vertices)
        vertex_attributes.update(make_controls(-body_cavity, len(vertices)))
        vertices.extend(make_vertices(xy_body, 0.0, body_cavity))
        vertex_attributes.update(make_controls(-body_cavity, len(vertices)))
        vertices.extend(make_vertices(xy_body, contact_height, body_cavity))
        vertex_attributes.update(make_controls(-body_cavity, len(vertices)))
        vertices.extend(make_vertices(xy_body, z_body, body_cavity))

        vertex_attributes.update(make_radial_controls(lid_roundness, bond_tension, len(vertices)))
        vertices.extend(make_vertices(xy_bond_outer, z_body, lid_roundness))
        vertex_attributes.update(make_axial_controls(lid_roundness, -bond_tension, len(vertices)))
        vertices.extend(make_vertices(xy_bond_inner, z_bond, lid_roundness))

        vertex_attributes.update(make_controls(lid_roundness, len(vertices)))
        vertices.extend(make_vertices(xy_lid, z_bond, lid_roundness))
        vertex_attributes.update(make_controls(lid_roundness, len(vertices)))
        vertices.extend(make_vertices(xy_lid, z_lid, lid_roundness))
        top_n = len(vertices)
        vertices.extend(make_top_vertices(xy_lid, z_lid, lid_roundness))

        if contact_count == 4:
            bottom_faces = make_bot_faces_4(0, bot_n)
            bottom_edges = make_bot_edges(bottom_faces[0] + bottom_faces[2], plane_resolution)
        else:
            bottom_faces = make_bot_faces_2(0, bot_n)
            bottom_edges = make_bot_edges(bottom_faces[0] + bottom_faces[2], plane_resolution)

        edges = bottom_edges[0]
        edge_attributes = bottom_edges[1]

        for i in range(0, (top_n - bot_n) // 8):
            circle = [list(range(bot_n + i * 8, bot_n + (i + 1) * 8)) + [bot_n + i * 8]]
            edges.extend(circle)

            for j, edge in enumerate(bezier.unpack_edges(circle)):
                key = tuple(edge)
                edge_attributes[key] = {}

                if j % 2 == 0:
                    edge_attributes[key][bezier.RESOLUTION] = arc_resolution
                if i == 5:
                    edge_attributes[key][bezier.INVERSION] = True

            if i > 0:
                lines = [[bot_n + (i - 1) * 8 + j, bot_n + i * 8 + j] for j in range(0, 8)]
                edges.extend(lines)

                for edge in lines:
                    key = tuple(sorted(edge))
                    if i == 3:
                        edge_attributes[key] = {bezier.RESOLUTION: plane_resolution}
                    elif i == 4:
                        edge_attributes[key] = {bezier.RESOLUTION: arc_resolution}

        edges.extend([list(range(top_n, len(vertices))) + [top_n]])
        for i in range(8):
            edges.append([len(vertices) - 1 - i // 2, top_n - 1 - i])

        body_faces = bottom_faces[0]
        body_face_attributes = bottom_faces[1]
        bond_faces = bottom_faces[2]
        bond_face_attributes = bottom_faces[3]
        lid_faces = []
        lid_face_attributes = {}

        for i in range(0, (top_n - bot_n) // 8 - 1):
            face_indices = [
                [
                    bot_n + (i + 1) * 8 + j,
                    bot_n + (i + 1) * 8 + (j + 1) % 8,
                    bot_n + i * 8 + (j + 1) % 8,
                    bot_n + i * 8 + j
                ]
                for j in range(0, 8)
            ]

            if i < 3:
                if i == 0:
                    body_faces.extend([face for i, face in enumerate(face_indices) if i % 2 == 1])
                    bond_faces.extend([face for i, face in enumerate(face_indices) if i % 2 == 0])
                else:
                    body_faces.extend(face_indices)
            elif i < 5:
                bond_faces.extend(face_indices)
            else:
                lid_faces.extend(face_indices)

        for i in range(4):
            indices = [len(vertices) - 1 - i, top_n - 1 - i * 2, top_n - 2 - i * 2]
            lid_faces.append(indices)
            lid_face_attributes[tuple(sorted(indices))] = {
                bezier.FUNCTOR: primitives.asymmetric_face_functor
            }

            lid_faces.append([
                len(vertices) - 1 - i,
                top_n - 2 - i * 2,
                top_n - 1 - ((i + 1) % 4) * 2,
                len(vertices) - 1 - (i + 1) % 4
            ])
        lid_faces.append(list(range(len(vertices) - 1, top_n - 1, -1)))

        body_vertex_attributes = copy.deepcopy(vertex_attributes)
        bond_vertex_attributes = copy.deepcopy(vertex_attributes)
        lid_vertex_attributes = copy.deepcopy(vertex_attributes)

        body_to_bond_lower_threshold = bot_n + 2 * 8
        bond_prev_layer = bot_n + 4 * 8
        bond_next_layer = bot_n + 6 * 8
        lid_prev_layer = bot_n + 5 * 8

        for key in body_vertex_attributes:
            if key < lid_prev_layer:
                # Remove lower vertices
                lid_vertex_attributes[key][bezier.DISCARD] = True

            if key >= bond_next_layer:
                # Remove upper vertices
                bond_vertex_attributes[key][bezier.DISCARD] = True
            if key >= body_to_bond_lower_threshold:
                # Hide bond joints for adjacent vertices
                bond_vertex_attributes[key][bezier.HIDDEN] = True

            if key >= bond_prev_layer:
                # Remove upper vertices
                body_vertex_attributes[key][bezier.DISCARD] = True
            if key < body_to_bond_lower_threshold:
                # Hide body vertex joints of the first layer
                body_vertex_attributes[key][bezier.HIDDEN] = True

        body_edge_attributes = copy.deepcopy(edge_attributes)
        bond_edge_attributes = copy.deepcopy(edge_attributes)

        # Handle edges of the first layer: even edges to bond mesh, odd edges to body mesh
        hidden_circle = [list(range(bot_n, bot_n + 8)) + [bot_n]]
        for i, edge in enumerate(bezier.unpack_edges(hidden_circle)):
            key = tuple(edge)
            if i % 2 == 0:
                body_edge_attributes[key][bezier.HIDDEN] = True
            else:
                bond_edge_attributes[key][bezier.HIDDEN] = True
        # Hide intermediate horizontal bond edges
        for i in (2, 5):
            hidden_circle = [list(range(bot_n + i * 8, bot_n + (i + 1) * 8)) + [bot_n + i * 8]]
            for edge in bezier.unpack_edges(hidden_circle):
                key = tuple(edge)
                bond_edge_attributes[key][bezier.HIDDEN] = True
        # Handle vertical edges of first two layers: first layer to bond mesh, second layer to body mesh
        for i in (1, 2):
            lines = [[bot_n + (i - 1) * 8 + j, bot_n + i * 8 + j] for j in range(8)]
            for edge in lines:
                key = tuple(sorted(edge))
                if i == 2:
                    bond_edge_attributes[key] = {bezier.HIDDEN: True}
                else:
                    body_edge_attributes[key] = {bezier.HIDDEN: True}

        body = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=body_faces,
            chamfer=body_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=body_vertex_attributes,
            edge_attributes=body_edge_attributes,
            face_attributes=body_face_attributes
        )
        bond = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=bond_faces,
            chamfer=body_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=bond_vertex_attributes,
            edge_attributes=bond_edge_attributes,
            face_attributes=bond_face_attributes
        )
        lid = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=lid_faces,
            chamfer=body_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=lid_vertex_attributes,
            edge_attributes=edge_attributes,
            face_attributes=lid_face_attributes
        )

        return tuple(bezier.patch_to_mesh(patch.build()) for patch in (body, bond, lid))

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(descriptor['body']['size'])
        body_chamfer = min(CrystalMetalCapSMD.DEFAULT_CHAMFER, min(body_size) / 20.0)
        body_cavity = body_chamfer * 3.0
        bond_height = body_size[2] / 10.0
        bond_width = min(body_size[:2]) / 20.0
        lid_height = body_size[2] / 5.0
        lid_roundness = max(body_size[:2] / 10.0)
        contact_count = descriptor['pins']['count']
        contact_height = body_size[2] / 3.0
        contact_offset = body_cavity / math.sqrt(2.0)
        contact_size = primitives.hmils(descriptor['pins']['size']) - body_cavity

        if contact_count not in (2, 4):
            raise ValueError()

        body_mesh, bond_mesh, lid_mesh = CrystalMetalCapSMD.make_crystal_parts(
            body_size=body_size,
            body_cavity=body_cavity,
            body_chamfer=body_chamfer,
            contact_count=contact_count,
            contact_height=contact_height,
            contact_offset=contact_offset,
            contact_size=contact_size,
            bond_height=bond_height,
            bond_offset=body_cavity,
            bond_width=bond_width,
            lid_chamfer=body_chamfer,
            lid_height=lid_height,
            lid_roundness=lid_roundness,

            arc_resolution=resolutions['arc'],
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line'],
            plane_resolution=max(resolutions['line'], 2)
        )

        if 'Crystal.Body' in materials:
            body_mesh.appearance().material = materials['Crystal.Body']
        if 'Crystal.Cap' in materials:
            lid_mesh.appearance().material = materials['Crystal.Cap']
        if 'Crystal.Lead' in materials:
            bond_mesh.appearance().material = materials['Crystal.Lead']

        return [body_mesh, bond_mesh, lid_mesh]


class CrystalSMD(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(CrystalSMD.PIVOT_BOUNDING_BOX_CENTER)

class CrystalTH(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(CrystalTH.PIVOT_BOUNDING_BOX_CENTER)

class CrystalMetalCapSMD2(CrystalMetalCapSMD):
    pass

class CrystalMetalCapSMD4(CrystalMetalCapSMD):
    pass


types = [
    CrystalSMD,
    CrystalMetalCapSMD2,
    CrystalMetalCapSMD4,
    CrystalTH
]
