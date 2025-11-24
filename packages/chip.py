#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chip.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy

import primitives
from packages import generic
from wrlconv import curves
from wrlconv import geometry
from wrlconv import model


class ChipBase:
    DEFAULT_CHAMFER = primitives.hmils(0.1)

    def __init__(self, material):
        self.material = material

    @staticmethod
    def make_chip(body_size, lead_width, chamfer, edge_resolution, line_resolution):
        case_chamfer = chamfer / (2.0 * math.sqrt(2.0))

        lead_size = numpy.array([lead_width, body_size[1], body_size[2]])
        ceramic_size = numpy.array([
            body_size[0] - 2.0 * lead_width,
            body_size[1] - 2.0 * case_chamfer,
            body_size[2] - 2.0 * case_chamfer])

        leads = primitives.make_chip_leads(case_size=ceramic_size, lead_size=lead_size,
            case_chamfer=case_chamfer, lead_chamfer=chamfer,
            edge_resolution=edge_resolution, line_resolution=line_resolution)
        leads.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))
        body = primitives.make_chip_body(size=ceramic_size, chamfer=case_chamfer,
            edge_resolution=edge_resolution)
        body.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))

        return [body, leads]

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(numpy.array(descriptor['body']['size']))
        lead_width = primitives.hmils(descriptor['pins']['width'])
        chamfer_from_size = min(body_size[1] * 0.1, body_size[2] * 0.1)

        meshes = ChipBase.make_chip(
            body_size=body_size,
            lead_width=lead_width,
            chamfer=max(chamfer_from_size, ChipBase.DEFAULT_CHAMFER),
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )

        if f'{self.material}.Ceramic' in materials:
            meshes[0].appearance().material = materials[f'{self.material}.Ceramic']
        if f'{self.material}.Lead' in materials:
            meshes[1].appearance().material = materials[f'{self.material}.Lead']
        return meshes


class ChipResistor:
    DEFAULT_CHAMFER = primitives.hmils(0.1)

    def __init__(self):
        self.material = 'ChipResistor'

    @staticmethod
    def make_body_edge(beg, end, v0, v1, resolution, inverse):
        edge_roundness = 1.0 / math.sqrt(2.0)
        line_roundness = 1.0 / 3.0

        p0 = beg + v0
        p1 = beg + v1
        p2 = end + v1
        p3 = end + v0
        t0 = -v0 * edge_roundness
        t1 = -v1 * edge_roundness
        t2 = -v1 * edge_roundness
        t3 = -v0 * edge_roundness

        p03_vec = (p3 - p0) * line_roundness
        p21_vec = (p1 - p2) * line_roundness

        p12_vec = -p21_vec
        p30_vec = -p03_vec

        line0 = (p1, p1 + t1, p0 + t0, p0)
        edge1 = (p1 + p12_vec, p0 + p03_vec)
        edge2 = (p2 + p21_vec, p3 + p30_vec)
        line3 = (p2, p2 + t2, p3 + t3, p3)

        line1 = (
            edge1[0],
            edge1[0] + t1,
            edge1[1] + t0,
            edge1[1]
        )
        line2 = (
            edge2[0],
            edge2[0] + t1,
            edge2[1] + t0,
            edge2[1]
        )

        return curves.BezierQuad(line0, line1, line2, line3, resolution, inverse)

    @staticmethod
    def make_body_corner(beg, end, v0, v1, resolution, inverse):
        slope = 0.5
        edge_roundness = 1.0 / math.sqrt(2.0)
        line_roundness = 1.0 / 3.0
        pb = end + v0
        pc = end + v1
        a = (
            beg,
            beg + (end + v0 * slope - beg) * edge_roundness,
            beg + (end + v1 * slope - beg) * edge_roundness
        )
        b = (pb, pb - v0 * edge_roundness, pb + (beg - end) * line_roundness)
        c = (pc, pc + (beg - end) * line_roundness, pc - v1 * edge_roundness)
        mean = (beg + pb + pc) / 3.0
        return curves.BezierTri(a, b, c, mean, resolution, inverse)

    @staticmethod
    def make_body_side(top_beg, top_end, bot_beg, bot_end, v0, resolution, inverse, pull=None):
        slope = 0.5
        edge_roundness = (1.0 / math.sqrt(2.0)) if v0 is not None else (1.0 / 3.0)
        line_roundness = 1.0 / 3.0

        p0 = top_beg
        p1 = (top_end - v0) if v0 is not None else top_end
        p2 = (bot_end + v0) if v0 is not None else bot_end
        p3 = bot_beg
        t1 = (top_beg - top_end) * line_roundness
        t2 = (bot_beg - bot_end) * line_roundness
        if v0 is not None:
            t0 = (p1 + v0 * slope - top_beg) * edge_roundness
            t3 = (p2 - v0 * slope - bot_beg) * edge_roundness
        else:
            t0 = (p1 - top_beg) * edge_roundness
            t3 = (p2 - bot_beg) * edge_roundness

        p03_vec = (p3 - p0) * line_roundness
        p21_vec = (p1 - p2) * line_roundness

        p12_vec = -p21_vec
        p30_vec = -p03_vec

        line0 = (p1, p1 + t1, p0 + t0, p0)
        edge1 = (p1 + p12_vec, p0 + p03_vec)
        edge2 = (p2 + p21_vec, p3 + p30_vec)
        line3 = (p2, p2 + t2, p3 + t3, p3)

        line1 = (
            edge1[0],
            edge1[0] + t1,
            edge1[1] + t0,
            edge1[1]
        )
        line2 = (
            edge2[0],
            edge2[0] + t1,
            edge2[1] + t0,
            edge2[1]
        )

        if pull is None:
            points = None
            resolution_smooth = resolution
        else:
            steps = ((1.0 - 2.0 * pull) / (resolution[0]), 1.0 / (resolution[1]))
            points = [
                [pull + i * steps[0] for i in range(0, resolution[0] + 1)],
                [i * steps[1] for i in range(0, resolution[1] + 1)]
            ]
            points[0] = [0.0, *points[0], 1.0]
            resolution_smooth = (resolution[0] + 2, resolution[1])

        return curves.BezierQuad(line0, line1, line2, line3, resolution_smooth, inverse, points)

    @staticmethod
    def make_body_path_face(vertices, normal, offset, scale, resolution, pull):
        mesh = model.Mesh()
        for vertex in vertices:
            mesh.geo_vertices.append(vertex * scale + offset)

        beg_index, end_index = 0, len(mesh.geo_vertices) - 1
        beg, end = mesh.geo_vertices[beg_index], mesh.geo_vertices[end_index]

        if pull is not None:
            side_vector = end - beg
            step = side_vector * (1.0 - 2.0 * pull) / resolution
            step_offset = side_vector * pull
            mesh.geo_vertices.append(beg + step_offset)
            for i in range(1, resolution):
                mesh.geo_vertices.append(beg + step_offset + step * i)
            mesh.geo_vertices.append(end - step_offset)
        else:
            step = (end - beg) / resolution
            for i in range(1, resolution):
                mesh.geo_vertices.append(beg + step * i)

        mean = numpy.zeros(3)
        for vertex in mesh.geo_vertices:
            mean += vertex
        mean /= len(mesh.geo_vertices)

        vertices = dict(zip(list(range(0, len(mesh.geo_vertices))), mesh.geo_vertices))
        indices = [x[0] for x in geometry.sort_vertices_by_angle(vertices, mean, normal)]
        count = len(vertices)

        if pull is not None:
            for vertex_index in vertices:
                vertex = mesh.geo_vertices[vertex_index]
                pulled_vertex = vertex - (vertex - mean) * pull * 2.0
                mesh.geo_vertices.append(pulled_vertex)

        mean_index = len(mesh.geo_vertices)
        mesh.geo_vertices.append(mean)

        polygons = []
        if pull is not None:
            for i in range(0, count):
                index_0, index_1 = indices[i], indices[(i + 1) % count]
                if ((index_0 in (beg_index, end_index) or index_1 in (beg_index, end_index))
                    and (index_0 > end_index or index_1 > end_index)):
                    if index_0 > index_1:
                        polygons.append([count + index_1, index_0, index_1])
                        polygons.append([count + index_1, count + index_0, index_0])
                    else:
                        polygons.append([count + index_0, index_0, index_1])
                        polygons.append([count + index_1, count + index_0, index_1])
                    continue
                polygons.append([index_0, index_1, count + index_1, count + index_0])
            for i in range(0, count):
                polygons.append([
                    count + indices[i],
                    count + indices[(i + 1) % count],
                    mean_index
                ])
        else:
            for i in range(0, count):
                polygons.append([
                    indices[i],
                    indices[(i + 1) % count],
                    mean_index
                ])

        mesh.geo_polygons.extend(polygons)
        return mesh

    @staticmethod
    def make_resistor_body(body_length, lead_thickness, lead_length, lead_width, lead_height,
                           lead_bridge_length, chamfer, bridge_resolution, slope_resolution,
                           edge_resolution, line_resolution):
        pin_path = ChipResistor.make_resistor_contact_curve(lead_thickness, lead_length,
            lead_height, lead_bridge_length, chamfer, bridge_resolution, slope_resolution,
            edge_resolution, line_resolution)

        # Remove first segment
        pin_path = pin_path[1:]
        # Remove two last segments
        if bridge_resolution > 0:
            pin_path = pin_path[:-1]

        points = []
        [points.extend(element.tessellate()) for element in pin_path]
        path_points = curves.optimize(points)

        beg, end = path_points[0], path_points[-1]
        corner_shift = numpy.array([chamfer * 3.0, 0.0, 0.0])
        edge_offset_x = numpy.array([body_length / 2.0, 0.0, 0.0])
        edge_offset_y = numpy.array([0.0, lead_width / 2.0, 0.0])
        edge_pull = (chamfer * math.pi / 2.0) \
            / (lead_height - 2.0 * (chamfer + lead_thickness)) / edge_resolution

        corner_points = [
            (
                numpy.array([-beg[0], *beg[1:]]) + edge_offset_x + edge_offset_y,
                numpy.array([-end[0], *end[1:]]) + edge_offset_x + edge_offset_y
            ), (
                beg - edge_offset_x + edge_offset_y,
                end - edge_offset_x + edge_offset_y
            ), (
                beg - edge_offset_x - edge_offset_y,
                end - edge_offset_x - edge_offset_y
            ), (
                numpy.array([-beg[0], *beg[1:]]) + edge_offset_x - edge_offset_y,
                numpy.array([-end[0], *end[1:]]) + edge_offset_x - edge_offset_y
            )
        ]

        meshes = []
        vdown = numpy.array([0.0, 0.0, -1.0]) * chamfer
        vside = numpy.array([0.0, 1.0, 0.0]) * chamfer

        # Body edges

        meshes.append(ChipResistor.make_body_edge(
            corner_points[0][0] - corner_shift, corner_points[1][0] + corner_shift,
            -vdown, -vside, (line_resolution, edge_resolution), False))
        meshes.append(ChipResistor.make_body_edge(
            corner_points[0][1] - corner_shift, corner_points[1][1] + corner_shift,
            vdown, -vside, (line_resolution, edge_resolution), True))
        meshes.append(ChipResistor.make_body_edge(
            corner_points[2][0] + corner_shift, corner_points[3][0] - corner_shift,
            -vdown, vside, (line_resolution, edge_resolution), False))
        meshes.append(ChipResistor.make_body_edge(
            corner_points[2][1] + corner_shift, corner_points[3][1] - corner_shift,
            vdown, vside, (line_resolution, edge_resolution), True))

        # Body corners, side one

        meshes.append(ChipResistor.make_body_corner(
            corner_points[0][0], corner_points[0][0] - corner_shift,
            -vdown, -vside, edge_resolution, False))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[0][1], corner_points[0][1] - corner_shift,
            vdown, -vside, edge_resolution, True))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[1][0], corner_points[1][0] + corner_shift,
            -vdown, -vside, edge_resolution, True))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[1][1], corner_points[1][1] + corner_shift,
            vdown, -vside, edge_resolution, False))

        # Body corners, side two

        meshes.append(ChipResistor.make_body_corner(
            corner_points[2][0], corner_points[2][0] + corner_shift,
            -vdown, vside, edge_resolution, False))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[2][1], corner_points[2][1] + corner_shift,
            vdown, vside, edge_resolution, True))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[3][0], corner_points[3][0] - corner_shift,
            -vdown, vside, edge_resolution, True))
        meshes.append(ChipResistor.make_body_corner(
            corner_points[3][1], corner_points[3][1] - corner_shift,
            vdown, vside, edge_resolution, False))

        # Vertical stripes

        meshes.append(ChipResistor.make_body_side(
            corner_points[0][0], corner_points[0][0] - corner_shift,
            corner_points[0][1], corner_points[0][1] - corner_shift,
            vdown, (line_resolution, edge_resolution), False, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[1][0], corner_points[1][0] + corner_shift,
            corner_points[1][1], corner_points[1][1] + corner_shift,
            vdown, (line_resolution, edge_resolution), True, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[2][0], corner_points[2][0] + corner_shift,
            corner_points[2][1], corner_points[2][1] + corner_shift,
            vdown, (line_resolution, edge_resolution), False, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[3][0], corner_points[3][0] - corner_shift,
            corner_points[3][1], corner_points[3][1] - corner_shift,
            vdown, (line_resolution, edge_resolution), True, edge_pull))

        # Horizontal stripes

        meshes.append(ChipResistor.make_body_side(
            corner_points[0][0], corner_points[0][0] - corner_shift,
            corner_points[3][0], corner_points[3][0] - corner_shift,
            vside, (line_resolution, edge_resolution), True, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[0][1], corner_points[0][1] - corner_shift,
            corner_points[3][1], corner_points[3][1] - corner_shift,
            vside, (line_resolution, edge_resolution), False, edge_pull))

        meshes.append(ChipResistor.make_body_side(
            corner_points[1][0], corner_points[1][0] + corner_shift,
            corner_points[2][0], corner_points[2][0] + corner_shift,
            vside, (line_resolution, edge_resolution), False, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[1][1], corner_points[1][1] + corner_shift,
            corner_points[2][1], corner_points[2][1] + corner_shift,
            vside, (line_resolution, edge_resolution), True, edge_pull))

        # Top and bottom planes

        meshes.append(ChipResistor.make_body_side(
            corner_points[0][0] - corner_shift - vside,
            corner_points[1][0] + corner_shift - vside,
            corner_points[3][0] - corner_shift + vside,
            corner_points[2][0] + corner_shift + vside,
            None, (line_resolution, line_resolution), True, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[0][1] - corner_shift - vside,
            corner_points[1][1] + corner_shift - vside,
            corner_points[3][1] - corner_shift + vside,
            corner_points[2][1] + corner_shift + vside,
            None, (line_resolution, line_resolution), False, edge_pull))

        # Left and right planes

        meshes.append(ChipResistor.make_body_side(
            corner_points[0][0] - corner_shift - vdown,
            corner_points[1][0] + corner_shift - vdown,
            corner_points[0][1] - corner_shift + vdown,
            corner_points[1][1] + corner_shift + vdown,
            None, (line_resolution, line_resolution), False, edge_pull))
        meshes.append(ChipResistor.make_body_side(
            corner_points[2][0] + corner_shift - vdown,
            corner_points[3][0] - corner_shift - vdown,
            corner_points[2][1] + corner_shift + vdown,
            corner_points[3][1] - corner_shift + vdown,
            None, (line_resolution, line_resolution), False, edge_pull))

        # Fill contact faces

        meshes.append(ChipResistor.make_body_path_face(path_points, -vside,
            -edge_offset_x - edge_offset_y, numpy.array([1.0, 1.0, 1.0]),
            line_resolution, edge_pull))
        meshes.append(ChipResistor.make_body_path_face(path_points, -vside,
            edge_offset_x - edge_offset_y, numpy.array([-1.0, 1.0, 1.0]),
            line_resolution, edge_pull))
        meshes.append(ChipResistor.make_body_path_face(path_points, vside,
            -edge_offset_x + edge_offset_y, numpy.array([1.0, 1.0, 1.0]),
            line_resolution, edge_pull))
        meshes.append(ChipResistor.make_body_path_face(path_points, vside,
            edge_offset_x + edge_offset_y, numpy.array([-1.0, 1.0, 1.0]),
            line_resolution, edge_pull))

        body = meshes[0]
        for mesh in meshes[1:]:
            body.append(mesh)
        body.optimize()
        return body

    @staticmethod
    def make_resistor_contact_curve(lead_thickness, lead_length, lead_height, lead_bridge_length,
                                    chamfer, bridge_resolution, slope_resolution, edge_resolution,
                                    line_resolution):
        weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
        parts = []

        bot_offset, top_offset = lead_thickness, lead_height - lead_thickness

        parts.append(curves.Line(
            (lead_length, 0.0, bot_offset),
            (lead_length - chamfer, 0.0, bot_offset),
            edge_resolution
        ))

        parts.append(curves.Line(
            (lead_length - chamfer, 0.0, bot_offset),
            (lead_thickness * 2.0, 0.0, bot_offset),
            line_resolution
        ))

        parts.append(curves.Bezier(
            (lead_thickness * 2.0, 0.0, bot_offset),
            (-lead_thickness * weight, 0.0, 0.0),
            (lead_thickness, 0.0, bot_offset + lead_thickness),
            (0.0, 0.0, -lead_thickness * weight),
            slope_resolution
        ))

        parts.append(curves.Line(
            (lead_thickness, 0.0, bot_offset + lead_thickness),
            (lead_thickness, 0.0, top_offset - lead_thickness),
            line_resolution
        ))

        parts.append(curves.Bezier(
            (lead_thickness, 0.0, top_offset - lead_thickness),
            (0.0, 0.0, lead_thickness * weight),
            (lead_thickness * 2.0, 0.0, top_offset),
            (-lead_thickness * weight, 0.0, 0.0),
            slope_resolution
        ))

        if bridge_resolution > 0:
            parts.append(curves.Line(
                (lead_thickness * 2.0, 0.0, top_offset),
                (lead_length, 0.0, top_offset),
                line_resolution
            ))

            parts.append(curves.Line(
                (lead_length, 0.0, top_offset),
                (lead_length + lead_bridge_length, 0.0, top_offset),
                bridge_resolution
            ))
        else:
            parts.append(curves.Line(
                (lead_thickness * 2.0, 0.0, top_offset),
                (lead_length + lead_bridge_length, 0.0, top_offset),
                line_resolution
            ))

        return parts

    @staticmethod
    def make_resistor_contact(lead_thickness, lead_length, lead_width, lead_height,
                              lead_bridge_length, lead_bridge_width, chamfer,
                              bridge_resolution, slope_resolution,
                              edge_resolution, line_resolution):
        roundness = chamfer / math.sqrt(2.0)

        pin_path = ChipResistor.make_resistor_contact_curve(lead_thickness, lead_length,
            lead_height, lead_bridge_length, chamfer, bridge_resolution, slope_resolution,
            edge_resolution, line_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_path]
        path_points = curves.optimize(points)

        pin_shape_size = [lead_thickness, lead_width]
        pin_shape = primitives.make_rounded_rect_half(pin_shape_size, False, roundness,
            edge_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_shape]
        shape_transform = model.Transform(matrix=model.rpy_to_matrix((0.0, 0.0, math.pi)))
        shape_points = [shape_transform.apply(point) for point in points]

        def mesh_scaling_func(number):
            chamfer_step = None
            slope_step = None

            if number <= edge_resolution:
                chamfer_step = number

            if bridge_resolution and number >= len(path_points) - bridge_resolution:
                slope_step = number - (len(path_points) - bridge_resolution) + 1

            if slope_step is not None:
                t_seg = math.cos(math.pi * (slope_step / bridge_resolution)) / 2.0 + 0.5
                t_offset = (pin_shape_size[1] - lead_bridge_width) * (1.0 - t_seg)
                t_scale = (pin_shape_size[1] - t_offset) / pin_shape_size[1]
                return numpy.array([1.0, t_scale, 1.0])

            if chamfer_step is not None:
                t_seg = math.sin((math.pi / 2.0) * (chamfer_step / edge_resolution))
                t_offset = chamfer * (1.0 - t_seg)
                t_scale = numpy.array([
                    (pin_shape_size[0] - t_offset) / pin_shape_size[0],
                    (pin_shape_size[1] - t_offset * 2.0) / pin_shape_size[1]
                ])
                return numpy.array([*t_scale, 1.0])

            return numpy.ones(3)

        pin_slices = curves.loft(path_points, shape_points, scaling=mesh_scaling_func)
        pin_mesh = primitives.build_loft_mesh(pin_slices, True, False)

        return pin_mesh

    @staticmethod
    def make_resistor_glass(lead_thickness, glass_length, glass_width, chamfer, edge_resolution,
                            line_resolution):
        roundness = chamfer / math.sqrt(2.0)
        top_part = primitives.make_chip_lead_cap(
            size=(glass_length, glass_width, (lead_thickness + roundness) * 2.0), chamfer=chamfer,
            invert=False, edge_resolution=edge_resolution, line_resolution=1, axis=2)

        bot_part_shape = primitives.make_rounded_rect(size=(glass_length, glass_width),
            roundness=roundness, segments=edge_resolution)
        bot_part_shape_points = []
        for element in bot_part_shape:
            bot_part_shape_points.extend(element.tessellate())
        bot_part_shape_points = curves.optimize(bot_part_shape_points)

        bot_part_path = curves.Line(
            (0.0, 0.0, 0.0),
            (0.0, 0.0, lead_thickness),
            line_resolution
        )
        bot_part_path_points = bot_part_path.tessellate()

        bot_part_slices = curves.loft(path=bot_part_path_points, shape=bot_part_shape_points)
        bot_part = primitives.build_loft_mesh(bot_part_slices, False, False)

        bot_part.append(top_part)
        bot_part.optimize()
        return bot_part

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(numpy.array(descriptor['body']['size']))
        pin_width = primitives.hmils(descriptor['pins']['width'])
        chamfer_from_size = min(body_size[1] * 0.1, body_size[2] * 0.05)
        thickness_from_size = chamfer_from_size * 2.0

        lead_length, lead_bridge_length = pin_width * 0.7, pin_width * 0.3

        meshes = []

        mesh_contact0 = ChipResistor.make_resistor_contact(
            lead_thickness=thickness_from_size,
            lead_length=lead_length,
            lead_width=body_size[1],
            lead_height=body_size[2],
            lead_bridge_length=lead_bridge_length,
            lead_bridge_width=body_size[1] * 0.8,
            chamfer=chamfer_from_size,
            bridge_resolution=resolutions['edge'],
            slope_resolution=resolutions['body'],
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if f'{self.material}.Lead' in materials:
            mesh_contact0.appearance().material = materials[f'{self.material}.Lead']
        mesh_contact1 = copy.deepcopy(mesh_contact0)
        mesh_contact0.translate((-body_size[0] / 2.0, 0.0, 0.0))
        mesh_contact1.rotate((0.0, 0.0, 1.0), math.pi)
        mesh_contact1.translate((body_size[0] / 2.0, 0.0, 0.0))
        mesh_contact1.rename()
        meshes.append(mesh_contact0)
        meshes.append(mesh_contact1)

        mesh_glass = ChipResistor.make_resistor_glass(
            lead_thickness=thickness_from_size,
            glass_length=body_size[0] - 2.0 * (lead_length + lead_bridge_length),
            glass_width=body_size[1] * 0.8 + chamfer_from_size * math.sqrt(2.0),
            chamfer=chamfer_from_size,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if f'{self.material}.Glass' in materials:
            mesh_glass.appearance().material = materials[f'{self.material}.Glass']
        mesh_glass.translate((0.0, 0.0, body_size[2] - thickness_from_size))
        meshes.append(mesh_glass)

        mesh_body = ChipResistor.make_resistor_body(
            body_length=body_size[0],
            lead_thickness=thickness_from_size,
            lead_length=lead_length,
            lead_width=body_size[1],
            lead_height=body_size[2],
            lead_bridge_length=lead_bridge_length,
            chamfer=chamfer_from_size,
            bridge_resolution=resolutions['edge'],
            slope_resolution=resolutions['body'],
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if f'{self.material}.Substrate' in materials:
            mesh_body.appearance().material = materials[f'{self.material}.Substrate']
        meshes.append(mesh_body)

        return meshes


class ChipShunt(ChipResistor):
    DEFAULT_CHAMFER = primitives.hmils(0.1)

    def __init__(self):
        self.material = 'ChipShunt'

    @staticmethod
    def make_resistor_element_curve(length, thickness, clearance, lead_length, line_resolution):
        parts = []

        slope = numpy.deg2rad(30.0)
        slope_length = clearance / math.sin(slope)

        x_offset = length / 2.0 - (lead_length + slope_length + thickness)
        z_offset = thickness / 2.0 + clearance

        parts.append(curves.Line(
            (-x_offset, 0.0, z_offset),
            ( x_offset, 0.0, z_offset),
            line_resolution
        ))
        return parts

    @staticmethod
    def make_resistor_contact_curve(length, thickness, clearance, lead_length, chamfer,
                                    slope_resolution, edge_resolution, line_resolution):
        weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
        parts = []

        x_offset, z_offset = length / 2.0, thickness / 2.0
        slope = numpy.deg2rad(30.0)
        slope_length = clearance / math.sin(slope)

        parts.append(curves.Line(
            (-x_offset, 0.0, z_offset),
            (-x_offset + chamfer, 0.0, z_offset),
            edge_resolution
        ))

        parts.append(curves.Line(
            (-x_offset + chamfer, 0.0, z_offset),
            (-x_offset + lead_length, 0.0, z_offset),
            line_resolution
        ))

        parts.append(curves.Bezier(
            (-x_offset + lead_length, 0.0, z_offset),
            (thickness * weight, 0.0, 0.0),
            (-x_offset + lead_length + slope_length, 0.0, z_offset + clearance),
            (-thickness * weight, 0.0, 0.0),
            slope_resolution
        ))

        parts.append(curves.Line(
            (-x_offset + lead_length + slope_length, 0.0, z_offset + clearance),
            (-x_offset + lead_length + slope_length + thickness, 0.0, z_offset + clearance),
            line_resolution
        ))

        return parts

    @staticmethod
    def make_resistor_contact(length, width, thickness, clearance, lead_length, chamfer,
                              slope_resolution, edge_resolution, line_resolution):
        roundness = chamfer / math.sqrt(2.0)

        pin_path = ChipShunt.make_resistor_contact_curve(length, thickness, clearance,
            lead_length, chamfer, slope_resolution, edge_resolution, line_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_path]
        path_points = curves.optimize(points)

        pin_shape_size = [thickness, width]
        pin_shape = primitives.make_rounded_rect(pin_shape_size, roundness, edge_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_shape]
        shape_transform = model.Transform(matrix=model.rpy_to_matrix((0.0, 0.0, math.pi)))
        shape_points = [shape_transform.apply(point) for point in points]

        def mesh_scaling_func(number):
            chamfer_step = None
            slope_step = None

            if number < edge_resolution:
                chamfer_step = number

            if chamfer_step is not None:
                t_seg = math.sin((math.pi / 2.0) * (chamfer_step / (edge_resolution - 1)))
                t_offset = chamfer * (1.0 - t_seg)

                t_scale = numpy.array([
                    (pin_shape_size[0] - t_offset) / pin_shape_size[0],
                    (pin_shape_size[1] - t_offset * 2.0) / pin_shape_size[1]
                ])
                return numpy.array([*t_scale, 1.0])

            return numpy.ones(3)

        pin_slices = curves.loft(path_points, shape_points, scaling=mesh_scaling_func)
        pin_mesh = primitives.build_loft_mesh(pin_slices, True, False)

        return pin_mesh

    @staticmethod
    def make_resistor_element(length, width, thickness, clearance, lead_length, chamfer,
                              edge_resolution, line_resolution):
        roundness = chamfer / math.sqrt(2.0)

        pin_path = ChipShunt.make_resistor_element_curve(length, thickness, clearance,
            lead_length, line_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_path]
        path_points = curves.optimize(points)

        pin_shape_size = [thickness, width]
        pin_shape = primitives.make_rounded_rect(pin_shape_size, roundness, edge_resolution)

        points = []
        [points.extend(element.tessellate()) for element in pin_shape]
        shape_transform = model.Transform(matrix=model.rpy_to_matrix((0.0, 0.0, math.pi)))
        shape_points = [shape_transform.apply(point) for point in points]

        pin_slices = curves.loft(path_points, shape_points)
        pin_mesh = primitives.build_loft_mesh(pin_slices, False, False)

        return pin_mesh

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(numpy.array(descriptor['body']['size']))
        clearance=primitives.hmils(descriptor['body']['clearance'])
        thickness=primitives.hmils(descriptor['body']['thickness'])
        pin_width = primitives.hmils(descriptor['pins']['width'])
        chamfer_from_size = body_size[2] * 0.05

        meshes = []

        mesh_contact0 = ChipShunt.make_resistor_contact(
            length=body_size[0],
            width=body_size[1],
            thickness=thickness,
            clearance=clearance,
            lead_length=pin_width,
            chamfer=chamfer_from_size,
            slope_resolution=resolutions['body'],
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if f'{self.material}.Lead' in materials:
            mesh_contact0.appearance().material = materials[f'{self.material}.Lead']
        mesh_contact1 = copy.deepcopy(mesh_contact0)
        mesh_contact1.rotate((0.0, 0.0, 1.0), math.pi)
        mesh_contact1.rename()
        meshes.append(mesh_contact0)
        meshes.append(mesh_contact1)

        mesh_body = ChipShunt.make_resistor_element(
            length=body_size[0],
            width=body_size[1],
            thickness=thickness,
            clearance=clearance,
            lead_length=pin_width,
            chamfer=chamfer_from_size,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if f'{self.material}.Alloy' in materials:
            mesh_body.appearance().material = materials[f'{self.material}.Alloy']
        meshes.append(mesh_body)

        return meshes


class ChipCapacitor(ChipBase):
    def __init__(self):
        super().__init__('ChipCapacitor')


class ChipFerrite(ChipBase):
    def __init__(self):
        super().__init__('ChipInductor')


class ChipInductor(ChipBase):
    def __init__(self):
        super().__init__('ChipInductor')


types = [
    ChipCapacitor,
    ChipFerrite,
    ChipInductor,
    ChipResistor,
    ChipShunt
]
