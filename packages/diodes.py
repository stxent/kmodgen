#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# diodes.py
# Copyright (C) 2026 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy as np

import bezier
import primitives
from wrlconv import curves


class MELF:
    def __init__(self):
        pass

    @staticmethod
    def make_melf_objects(body_length, body_radius, body_curvature, contact_chamfer, contact_length,
                          contact_radius, arc_resolution, edge_resolution, line_resolution,
                          band_length=None, band_offset=0.0):
        def make_vertex_group(x, r): # pylint: disable=invalid-name
            return [
                np.array([x, 0.0,   r]),
                np.array([x,   r, 0.0]),
                np.array([x, 0.0,  -r]),
                np.array([x,  -r, 0.0])
            ]

        def make_group(n, r, chamfer, _, resolution): # pylint: disable=invalid-name
            w = curves.calc_bezier_weight(angle=math.pi / 2.0)
            return {
                n + 0: {bezier.CHAMFER: chamfer, bezier.RESOLUTION: resolution, bezier.TENSION: {
                    n + 3: np.array([0.0, -w * r,    0.0]),
                    n + 1: np.array([0.0,  w * r,    0.0])
                }},
                n + 1: {bezier.CHAMFER: chamfer, bezier.RESOLUTION: resolution, bezier.TENSION: {
                    n + 0: np.array([0.0,    0.0,  w * r]),
                    n + 2: np.array([0.0,    0.0, -w * r])
                }},
                n + 2: {bezier.CHAMFER: chamfer, bezier.RESOLUTION: resolution, bezier.TENSION: {
                    n + 1: np.array([0.0,  w * r,    0.0]),
                    n + 3: np.array([0.0, -w * r,    0.0])
                }},
                n + 3: {bezier.CHAMFER: chamfer, bezier.RESOLUTION: resolution, bezier.TENSION: {
                    n + 2: np.array([0.0,    0.0, -w * r]),
                    n + 0: np.array([0.0,    0.0,  w * r])
                }}
            }

        def make_a_group(n, r, chamfer, tension, resolution): # pylint: disable=invalid-name
            linear_group = make_group(n, r, chamfer, tension, resolution)
            neighbors = list(range(n - 4, n)) if tension > 0.0 else list(range(n + 4, n + 8))
            for i, offset in enumerate(neighbors):
                linear_group[n + i][bezier.TENSION][offset] = np.array([tension, 0.0, 0.0])
            return linear_group

        def make_r_group(n, r, chamfer, tension, resolution): # pylint: disable=invalid-name
            linear_group = make_group(n, r, chamfer, tension, resolution)
            offset = list(range(n + 4, n + 8)) if tension > 0.0 else list(range(n - 4, n))
            tension = abs(tension)
            linear_group[n + 0][bezier.TENSION][offset[0]] = np.array([0.0,      0.0,  tension])
            linear_group[n + 1][bezier.TENSION][offset[1]] = np.array([0.0,  tension,      0.0])
            linear_group[n + 2][bezier.TENSION][offset[2]] = np.array([0.0,      0.0, -tension])
            linear_group[n + 3][bezier.TENSION][offset[3]] = np.array([0.0, -tension,      0.0])
            return linear_group

        r_contact = contact_radius
        x_contact_out = body_length / 2.0
        x_contact_in = body_length / 2.0 - contact_length

        body_tension = body_curvature * curves.calc_bezier_weight(angle=math.pi / 2.0)
        r_body_out = body_radius - body_curvature
        x_body_out = body_length / 2.0 - contact_length
        r_body_in = body_radius
        x_body_in = body_length / 2.0 - contact_length - body_curvature

        details = edge_resolution
        slices = [
            ( x_contact_out,  r_contact, contact_chamfer,           0.0, details,   make_group),
            (  x_contact_in,  r_contact, contact_chamfer,           0.0, details,   make_group),
            (    x_body_out, r_body_out, contact_chamfer,  body_tension, details, make_r_group),
            (     x_body_in,  r_body_in, contact_chamfer,  body_tension, details, make_a_group)
        ]

        if band_length is not None:
            r_band = body_radius
            x_band_out = band_length / 2.0 + band_offset
            x_band_in = -band_length / 2.0 + band_offset
            inverted_slices = (2, 7)

            slices += [
                (x_band_out, r_band, 0.0, 0.0, 1, make_group),
                ( x_band_in, r_band, 0.0, 0.0, 1, make_group)
            ]
        else:
            inverted_slices = (2, 5)

        slices += [
            (    -x_body_in,  r_body_in, contact_chamfer, -body_tension, details, make_a_group),
            (   -x_body_out, r_body_out, contact_chamfer, -body_tension, details, make_r_group),
            ( -x_contact_in,  r_contact, contact_chamfer,           0.0, details,   make_group),
            (-x_contact_out,  r_contact, contact_chamfer,           0.0, details,   make_group)
        ]

        vertices = []
        vertex_attributes = {}
        for entry in slices:
            vertex_attributes.update(entry[5](len(vertices), *entry[1:-1]))
            vertices += make_vertex_group(*entry[:2])
        vertices.append(np.array([ x_contact_out, 0.0, 0.0]))
        vertices.append(np.array([-x_contact_out, 0.0, 0.0]))

        body_vertex_attributes = copy.deepcopy(vertex_attributes)
        for i in list(range(inverted_slices[0])) + list(range(inverted_slices[1] + 1, len(slices))):
            for j in range(4):
                body_vertex_attributes[i * 4 + j][bezier.DISCARD] = True

        edges = []
        edge_attributes = {}
        for i in range(len(vertices) // 4):
            circle = [list(range(i * 4, (i + 1) * 4)) + [i * 4]]
            edges.extend(circle)
            for edge in bezier.unpack_edges(circle):
                key = tuple(edge)
                edge_attributes[key] = {bezier.RESOLUTION: arc_resolution}
                if i in inverted_slices:
                    edge_attributes[key][bezier.INVERSION] = True
        for i in range(4):
            edges.append([i + j * 4 for j in range(len(vertices) // 4)])
            edges.append([len(vertices) - 2, i])
            edges.append([len(vertices) - 1, len(vertices) - 3 - i])

            key = (inverted_slices[0] * 4 + i, (inverted_slices[0] + 1) * 4 + i)
            edge_attributes[key] = {bezier.RESOLUTION: arc_resolution}
            key = ((inverted_slices[1] - 1) * 4 + i, inverted_slices[1] * 4 + i)
            edge_attributes[key] = {bezier.RESOLUTION: arc_resolution}

        band_faces, body_faces, lead_faces = [], [], []
        for i in range(len(vertices) // 4 - 1):
            face_indices = [
                [i * 4 + 0, i * 4 + 1, (i + 1) * 4 + 1, (i + 1) * 4 + 0],
                [i * 4 + 1, i * 4 + 2, (i + 1) * 4 + 2, (i + 1) * 4 + 1],
                [i * 4 + 2, i * 4 + 3, (i + 1) * 4 + 3, (i + 1) * 4 + 2],
                [i * 4 + 3, i * 4 + 0, (i + 1) * 4 + 0, (i + 1) * 4 + 3]
            ]
            if i < inverted_slices[0] or i >= inverted_slices[1]:
                lead_faces.extend(face_indices)
            else:
                if band_length is not None and i == inverted_slices[0] + 2:
                    band_faces.extend(face_indices)
                else:
                    body_faces.extend(face_indices)

        start, center = 3, len(vertices) - 2
        top_face_indices = [(start - i, center) for i in range(4)]
        lead_faces.append(top_face_indices)
        start, center = len(vertices) - 6, len(vertices) - 1
        bot_face_indices = [(start + i, center) for i in range(4)]
        lead_faces.append(bot_face_indices)

        # Override top and bottom faces
        face_attributes = {}
        face_attributes[tuple(number[0] for number in top_face_indices)] = {
            bezier.FUNCTOR: primitives.circular_face_functor
        }
        face_attributes[tuple(number[0] for number in bot_face_indices)] = {
            bezier.FUNCTOR: primitives.circular_face_functor
        }

        body = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=body_faces,
            chamfer=contact_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=body_vertex_attributes,
            edge_attributes=edge_attributes
        )
        lead = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=lead_faces,
            chamfer=contact_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=vertex_attributes,
            edge_attributes=edge_attributes,
            face_attributes=face_attributes
        )
        if band_length is not None:
            band = bezier.BezierObject(
                vertices=vertices,
                edges=edges,
                faces=band_faces,
                chamfer=contact_chamfer,
                sharpness=math.pi * (5.0 / 6.0),
                edge_resolution=edge_resolution,
                line_resolution=line_resolution,
                vertex_attributes=body_vertex_attributes,
                edge_attributes=edge_attributes
            )

        if band_length is not None:
            return tuple(bezier.patch_to_mesh(patch.build()) for patch in (body, lead, band))
        return (bezier.patch_to_mesh(body.build()), bezier.patch_to_mesh(lead.build()), None)

    def generate(self, materials, resolutions, _, descriptor):
        length = primitives.hmils(descriptor['body']['length'])
        body_curvature = primitives.hmils(descriptor['body']['radius'] / 5.0)
        body_radius = primitives.hmils(descriptor['body']['radius'])
        contact_chamfer = primitives.hmils(descriptor['pins']['length'] / 10.0)
        contact_length = primitives.hmils(descriptor['pins']['length'])
        contact_radius = primitives.hmils(descriptor['pins']['radius'])

        try:
            band_length = primitives.hmils(descriptor['band']['length'])
        except KeyError:
            band_length = None

        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0

        body_mesh, lead_mesh, band_mesh = MELF.make_melf_objects(
            body_length=length,
            body_radius=body_radius,
            body_curvature=body_curvature,
            contact_chamfer=contact_chamfer,
            contact_length=contact_length,
            contact_radius=contact_radius,
            arc_resolution=resolutions['circle'] // 4,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line'],
            band_length=band_length,
            band_offset=band_offset
        )

        meshes = [body_mesh, lead_mesh]
        if 'MELF.Glass' in materials:
            body_mesh.appearance().material = materials['MELF.Glass']
        if 'MELF.Lead' in materials:
            lead_mesh.appearance().material = materials['MELF.Lead']
        if band_mesh is not None and 'MELF.Band' in materials:
            meshes.append(band_mesh)
            band_mesh.appearance().material = materials['MELF.Band']

        for mesh in meshes:
            mesh.translate(np.array([0.0, 0.0, contact_radius]))
        return meshes


types = [MELF]
