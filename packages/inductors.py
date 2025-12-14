#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# inductors.py
# Copyright (C) 2025 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy as np

import primitives
from wrlconv import curves
from wrlconv import geometry
from wrlconv import model


class ChipOpenDrumInductor:
    DEFAULT_CHAMFER = primitives.hmils(0.1)


    class SliceSet:
        def __init__(self, layers, inverse):
            self.layers = layers
            self.inverse = inverse

        def mesh(self):
            return primitives.slice_connect_nearest(self.layers, self.inverse)


    def __init__(self):
        self.material = 'ChipOpenDrumInductor'

    @staticmethod
    def make_inductor_cap_shape(body_radius, bevel_height, hole_radius, hole_depth,
                                line_segments, arc_segments, corner_segments):
        corner_roundness = hole_radius / 2.0
        shape = []

        # Flat line on top of the package
        flat_line_y = body_radius - bevel_height
        bevel_asin = math.asin(flat_line_y / body_radius)
        flat_line_x = math.cos(bevel_asin) * body_radius

        # Round corner between flat line and arc
        rounded_bevel_x = flat_line_x + corner_roundness * 2.0
        rounded_bevel_acos = math.acos(rounded_bevel_x / body_radius)
        rounded_bevel_y = math.sin(rounded_bevel_acos) * body_radius
        rounded_bevel_angle = bevel_asin - rounded_bevel_acos
        rounded_bevel_weight = curves.calc_bezier_weight(angle=rounded_bevel_angle) * body_radius
        rounded_bevel_start = np.array([rounded_bevel_weight, 0.0])
        rounded_bevel_end = np.array([-math.sin(rounded_bevel_acos),
                                       math.cos(rounded_bevel_acos)]) * rounded_bevel_weight

        # Arc from flat line to the round corner near the wire hole
        hole_corner_y = hole_radius + corner_roundness
        hole_corner_asin = math.asin(hole_corner_y / body_radius)
        hole_corner_x = math.cos(hole_corner_asin) * body_radius
        arc_angle = rounded_bevel_acos - hole_corner_asin
        arc_weight = curves.calc_bezier_weight(angle=arc_angle) * body_radius
        arc_start = np.array([ math.sin(rounded_bevel_acos),
                              -math.cos(rounded_bevel_acos)]) * arc_weight
        arc_end = np.array([-math.sin(hole_corner_asin),
                             math.cos(hole_corner_asin)]) * arc_weight

        # Round corner between arc and wire hole
        hole_top_y = hole_radius
        hole_top_asin = math.asin(hole_top_y / body_radius)
        hole_top_x = math.cos(hole_top_asin) * body_radius - corner_roundness
        hole_corner_start = np.array([ math.sin(hole_corner_asin),
                                      -math.cos(hole_corner_asin)]) * corner_roundness
        hole_corner_end = np.array([corner_roundness, 0.0, 0.0])
        hole_depth_trunc = hole_depth - (body_radius - hole_top_x)

        # Flat line
        shape.append(curves.Line((-flat_line_x, flat_line_y, 0.0),
                                 ( flat_line_x, flat_line_y, 0.0), line_segments))

        # Corner
        shape.append(curves.Bezier((flat_line_x, flat_line_y, 0.0),
                                   (rounded_bevel_start[0], rounded_bevel_start[1], 0.0),
                                   (rounded_bevel_x, rounded_bevel_y, 0.0),
                                   (rounded_bevel_end[0], rounded_bevel_end[1], 0.0),
                                   corner_segments))

        # Arc
        shape.append(curves.Bezier((rounded_bevel_x, rounded_bevel_y, 0.0),
                                   (arc_start[0], arc_start[1], 0.0),
                                   (hole_corner_x, hole_corner_y, 0.0),
                                   (arc_end[0], arc_end[1], 0.0), arc_segments))

        # Corner
        shape.append(curves.Bezier((hole_corner_x, hole_corner_y, 0.0),
                                   (hole_corner_start[0], hole_corner_start[1], 0.0),
                                   (hole_top_x, hole_top_y, 0.0),
                                   (hole_corner_end[0], hole_corner_end[1], 0.0),
                                   corner_segments))

        # Wire hole
        shape.append(curves.Bezier((hole_top_x, hole_top_y, 0.0),
                                   (-hole_depth_trunc, 0.0, 0.0),
                                   (hole_top_x, -hole_top_y, 0.0),
                                   (-hole_depth_trunc, 0.0, 0.0), arc_segments * 2))

        # Mirrored segments: swap start and end, invert Y, than X, than Y
        shape.append(curves.Bezier((hole_top_x, -hole_top_y, 0.0),
                                   (hole_corner_end[0], -hole_corner_end[1], 0.0),
                                   (hole_corner_x, -hole_corner_y, 0.0),
                                   (hole_corner_start[0], -hole_corner_start[1], 0.0),
                                   corner_segments))
        shape.append(curves.Bezier((hole_corner_x, -hole_corner_y, 0.0),
                                   (arc_end[0], -arc_end[1], 0.0),
                                   (rounded_bevel_x, -rounded_bevel_y, 0.0),
                                   (arc_start[0], -arc_start[1], 0.0), arc_segments))
        shape.append(curves.Bezier((rounded_bevel_x, -rounded_bevel_y, 0.0),
                                   (rounded_bevel_end[0], -rounded_bevel_end[1], 0.0),
                                   (flat_line_x, -flat_line_y, 0.0),
                                   (rounded_bevel_start[0], -rounded_bevel_start[1], 0.0),
                                   corner_segments))
        shape.append(curves.Line(( flat_line_x, -flat_line_y, 0.0),
                                 (-flat_line_x, -flat_line_y, 0.0), line_segments))
        shape.append(curves.Bezier((-flat_line_x, -flat_line_y, 0.0),
                                   (-rounded_bevel_start[0], -rounded_bevel_start[1], 0.0),
                                   (-rounded_bevel_x, -rounded_bevel_y, 0.0),
                                   (-rounded_bevel_end[0], -rounded_bevel_end[1], 0.0),
                                   corner_segments))
        shape.append(curves.Bezier((-rounded_bevel_x, -rounded_bevel_y, 0.0),
                                   (-arc_start[0], -arc_start[1], 0.0),
                                   (-hole_corner_x, -hole_corner_y, 0.0),
                                   (-arc_end[0], -arc_end[1], 0.0), arc_segments))
        shape.append(curves.Bezier((-hole_corner_x, -hole_corner_y, 0.0),
                                   (-hole_corner_start[0], -hole_corner_start[1], 0.0),
                                   (-hole_top_x, -hole_top_y, 0.0),
                                   (-hole_corner_end[0], -hole_corner_end[1], 0.0),
                                   corner_segments))
        shape.append(curves.Bezier((-hole_top_x, -hole_top_y, 0.0),
                                   (hole_depth_trunc, 0.0, 0.0),
                                   (-hole_top_x, hole_top_y, 0.0),
                                   (hole_depth_trunc, 0.0, 0.0), arc_segments * 2))
        shape.append(curves.Bezier((-hole_top_x, hole_top_y, 0.0),
                                   (-hole_corner_end[0], hole_corner_end[1], 0.0),
                                   (-hole_corner_x, hole_corner_y, 0.0),
                                   (-hole_corner_start[0], hole_corner_start[1], 0.0),
                                   corner_segments))
        shape.append(curves.Bezier((-hole_corner_x, hole_corner_y, 0.0),
                                   (-arc_end[0], arc_end[1], 0.0),
                                   (-rounded_bevel_x, rounded_bevel_y, 0.0),
                                   (-arc_start[0], arc_start[1], 0.0), arc_segments))
        shape.append(curves.Bezier((-rounded_bevel_x, rounded_bevel_y, 0.0),
                                   (-rounded_bevel_end[0], rounded_bevel_end[1], 0.0),
                                   (-flat_line_x, flat_line_y, 0.0),
                                   (-rounded_bevel_start[0], rounded_bevel_start[1], 0.0),
                                   corner_segments))

        return shape

    @staticmethod
    def make_inductor_body(body_radius, body_height, disc_thickness, disc_bevel_height, pin_height,
                           inner_radius, hole_radius, chamfer, line_segments, arc_segments,
                           corner_segments, circle_segments):
        def shift_slice(points, offset):
            return [point + np.array([0.0, 0.0, offset]) for point in points]

        def make_center_line(vertices):
            box = model.calc_bounding_box(vertices)
            x_median = (box[0][0] + box[1][0]) / 2.0
            y_size = box[1][1] - box[0][1]
            return [
                np.array([x_median, -y_size / 3.0, 0.0]),
                np.array([x_median,  y_size / 3.0, 0.0])
            ]

        def make_center_hex(outer_radius, chamfer):
            radius = (outer_radius + chamfer * 2.0) / (math.sqrt(3.0) / 2.0)
            output = []
            for i in range(0, 8):
                angle = -((i * 2.0 + 1.0) / 16.0) * math.pi * 2.0
                point = np.array([
                    math.cos(angle) * radius,
                    math.sin(angle) * radius,
                    0.0
                ])
                output.append(point)
            return output

        def make_bottom_rect(radius, bevel):
            height = radius - bevel
            angle = math.asin(height / radius)
            width = math.cos(angle) * radius
            return ((-width, -(radius - bevel)), (width, radius - bevel))

        def make_left_contact_rect(radius, bevel):
            height = radius - bevel
            angle = math.asin(height / radius)
            width = math.cos(angle) * radius
            return ((-radius, -(radius - bevel)), (-width, radius - bevel))

        def select_bottom_points(shape):
            rect = make_bottom_rect(body_radius, disc_bevel_height)
            return [np.array([*point[:2], 0.0]) for point in shape
                    if curves.is_point_in_rect(rect, point)]

        def select_contact_points(shape):
            rect = make_left_contact_rect(body_radius, disc_bevel_height)
            points = [np.array([*point[:2], 0.0]) for point in shape
                      if curves.is_point_in_rect(rect, point)]
            points = sorted(points, key=lambda point: point[1])

            first, last = points[0], points[-1]
            median = (first + last) / 2.0
            dy = first[1] * 2.0 / 5
            points = [median + np.array([0.0, dy * 1.5, 0.0])] + points
            points = [median + np.array([0.0, dy * 0.5, 0.0])] + points
            points = points + [median - np.array([0.0, dy * 1.5, 0.0])]
            points = points + [median - np.array([0.0, dy * 0.5, 0.0])]
            return points

        hole_depth = hole_radius * 2.0
        disc_curve = ChipOpenDrumInductor.make_inductor_cap_shape(
            body_radius=body_radius,
            bevel_height=disc_bevel_height,
            hole_radius=hole_radius,
            hole_depth=hole_depth,
            line_segments=line_segments,
            arc_segments=arc_segments,
            corner_segments=corner_segments
        )

        interim_shape = make_center_hex(inner_radius, chamfer)

        disc_shape = []
        [disc_shape.extend(element.tessellate()) for element in disc_curve]
        disc_shape = curves.optimize(disc_shape)
        disc_shape = disc_shape[:-1]

        disc_shape_slices = [disc_shape]
        disc_shape_shifts = [0.0]
        bottom_offsets = [(0.0, 0.0)]

        for i in range(0, corner_segments):
            angle = (math.pi / 2.0) * ((i + 1) / corner_segments)
            radial_offset = (1.0 - math.cos(angle)) * chamfer
            vertical_offset = math.sin(angle) * chamfer

            shape = primitives.smart_scale(disc_shape, radial_offset)
            disc_shape_slices.append(shape)
            disc_shape_shifts.append(vertical_offset)
            bottom_offsets.append((radial_offset, vertical_offset))
        disc_shape_slices.append(primitives.smart_scale(disc_shape, chamfer * 2.0))
        disc_shape_shifts.append(chamfer)

        tube_shape = primitives.make_circle_outline(np.zeros(3), inner_radius + chamfer,
                                                    circle_segments)
        tube_shape.reverse()
        tube_shape_slices = [tube_shape]
        tube_shape_shifts = [0.0]

        for i in range(0, corner_segments):
            angle = (math.pi / 2.0) * ((corner_segments - (i + 1)) / corner_segments)
            radial_offset = math.cos(angle) * chamfer
            vertical_offset = (1.0 - math.sin(angle)) * chamfer

            shape = primitives.smart_scale(tube_shape, radial_offset)
            tube_shape_slices.append(shape)
            tube_shape_shifts.append(vertical_offset)

        parts = []

        # Part 1
        slices = []
        slices.append(shift_slice(disc_shape_slices[0], pin_height + disc_thickness - chamfer))
        slices.append(shift_slice(disc_shape_slices[0], pin_height + chamfer))
        parts.append(ChipOpenDrumInductor.SliceSet(slices, True))

        # Bottom part
        bottom = select_bottom_points(slices[-1])
        left_contact = select_contact_points(slices[-1])
        left_median = model.calc_median_point(left_contact)

        slices = []
        for i in range(0, len(bottom_offsets)):
            vertical_offset = pin_height + chamfer - bottom_offsets[i][1]
            scale = np.array([0.0, bottom_offsets[i][0], 0.0])
            slices.append(shift_slice(primitives.simple_scale(bottom, scale), vertical_offset))
        slices.append([model.calc_center_point(slices[-1])])
        parts.append(ChipOpenDrumInductor.SliceSet(slices, True))

        # Part 2
        slices = []
        for i in range(0, len(disc_shape_slices)):
            vertical_offset = pin_height + disc_thickness - chamfer + disc_shape_shifts[i]
            slices.append(shift_slice(disc_shape_slices[i], vertical_offset))

        slices.append(shift_slice(interim_shape, pin_height + disc_thickness))
        for i in range(0, len(tube_shape_slices)):
            vertical_offset = pin_height + disc_thickness + tube_shape_shifts[i]
            slices.append(shift_slice(tube_shape_slices[i], vertical_offset))
        slices.append(shift_slice(tube_shape_slices[-1], body_height - disc_thickness - chamfer))
        parts.append(ChipOpenDrumInductor.SliceSet(slices, False))

        # Part 3
        slices = []
        slices.append(shift_slice(disc_shape_slices[0], body_height - chamfer))
        for i in range(0, len(disc_shape_slices)):
            vertical_offset = body_height - disc_thickness + chamfer - disc_shape_shifts[i]
            slices.append(shift_slice(disc_shape_slices[i], vertical_offset))

        slices.append(shift_slice(interim_shape, body_height - disc_thickness))
        for i in range(0, len(tube_shape_slices)):
            vertical_offset = body_height - disc_thickness - tube_shape_shifts[i]
            slices.append(shift_slice(tube_shape_slices[i], vertical_offset))
        parts.append(ChipOpenDrumInductor.SliceSet(slices, True))

        # Part 4
        slices = []
        for i in range(0, len(disc_shape_slices)):
            vertical_offset = body_height - chamfer + disc_shape_shifts[i]
            slices.append(shift_slice(disc_shape_slices[i], vertical_offset))
        slices.append(shift_slice(interim_shape, body_height))
        slices.append([np.array([0.0, 0.0, body_height])])
        parts.append(ChipOpenDrumInductor.SliceSet(slices, False))

        # Contact part
        slices = [shift_slice(left_contact, pin_height + chamfer)]
        for i in range(0, len(bottom_offsets)):
            offset_h = bottom_offsets[i][0] / 4.0
            offset_v = (chamfer - bottom_offsets[i][1]) / 4.0
            slices.append(shift_slice(primitives.smart_scale(left_contact, offset_h,
                                                             left_median), offset_v))
        interim = shift_slice(primitives.smart_scale(left_contact, chamfer * 2.0,
                                                     left_median), offset_v)
        slices.append(interim)
        slices.append(shift_slice(make_center_line(interim), offset_v))
        left_contact_mesh = ChipOpenDrumInductor.SliceSet(slices, True).mesh()

        mesh = model.Mesh()
        for part in parts:
            mesh.append(part.mesh())
        mesh.optimize()

        return (mesh, left_contact_mesh)

    @staticmethod
    def make_inductor_wire(body_radius, body_height, disc_thickness, pin_height,
                           wire_radius, winding_radius, hole_radius, hole_depth, chamfer,
                           arc_segments, circle_segments, wire_segments):
        def calc_wire_to_pin_offset():
            corner_roundness = hole_radius / 2.0

            hole_corner_y = hole_radius + corner_roundness
            hole_corner_asin = math.asin(hole_corner_y / body_radius)

            hole_top_y = hole_radius
            hole_top_asin = math.asin(hole_top_y / body_radius)
            hole_top_x = math.cos(hole_top_asin) * body_radius - corner_roundness
            hole_corner_start = np.array([ math.sin(hole_corner_asin),
                                          -math.cos(hole_corner_asin)]) * corner_roundness
            hole_corner_end = np.array([corner_roundness, 0.0, 0.0])
            hole_depth_trunc = hole_depth - (body_radius - hole_top_x)

            hole_curve = curves.Bezier((hole_top_x, hole_top_y, 0.0),
                                       (-hole_depth_trunc, 0.0, 0.0),
                                       (hole_top_x, -hole_top_y, 0.0),
                                       (-hole_depth_trunc, 0.0, 0.0), 1)
            return hole_curve.point(0.5)

        winding_height = body_height - disc_thickness * 2.0 - pin_height - wire_radius * 2.0
        beg_angle, end_angle = math.pi / 8.0, math.pi * (7.0 / 8.0)
        arc_part = (end_angle - beg_angle) / (math.pi * 2.0)
        turn_count = winding_height / (wire_radius * 2.0)
        if turn_count % 1.0 < arc_part:
            turn_count -= 1.0
        turn_count = int(turn_count) + arc_part

        winding_offset_v = pin_height + disc_thickness + wire_radius
        winding_steps = round(turn_count * circle_segments)
        winding_step_ang = turn_count * math.pi * 2.0 / winding_steps
        winding_step_v = winding_height / winding_steps
        hole_edge_point = calc_wire_to_pin_offset()

        wire_roundness = math.sin(beg_angle) * (winding_radius + wire_radius)
        tension_ab_ba_weight = curves.calc_bezier_weight(angle=math.pi / 2.0) * wire_radius * 2.0

        # Bottom end of wire to the contact

        beg_point_a = np.array([
            hole_edge_point[0],
            0.0,
            (pin_height + chamfer) / 2.0
        ])
        beg_tension_ab = np.array([tension_ab_ba_weight, 0.0, 0.0])
        beg_tension_ba = np.array([0.0, 0.0, -tension_ab_ba_weight])
        beg_point_b = np.array([
            hole_edge_point[0] + wire_radius * 2.0,
            0.0,
            (pin_height + chamfer) / 2.0 + wire_radius * 2.0
        ])

        beg_point_c = np.array([
            hole_edge_point[0] + wire_radius * 2.0,
            0.0,
            pin_height + disc_thickness - wire_radius
        ])
        beg_tension_cd = np.array([0.0, 0.0, wire_radius * 3.0])
        beg_tension_dc = np.array([
            math.sin(beg_angle) * wire_roundness,
            -math.cos(beg_angle) * wire_roundness,
            0.0
        ])
        beg_point_d = np.array([
            math.cos(beg_angle) * (winding_radius + wire_radius),
            math.sin(beg_angle) * (winding_radius + wire_radius),
            winding_offset_v
        ])

        beg_curve_ab = curves.Bezier(beg_point_a, beg_tension_ab, beg_point_b, beg_tension_ba,
                                     arc_segments)
        beg_curve_bc = curves.Line(beg_point_b, beg_point_c, 1)
        beg_curve_cd = curves.Bezier(beg_point_c, beg_tension_cd, beg_point_d, beg_tension_dc,
                                     arc_segments * 2)

        beg_points_ab = beg_curve_ab.tessellate()
        beg_points_bc = beg_curve_bc.tessellate()
        beg_points_cd = beg_curve_cd.tessellate()
        beg_points = curves.connect_paths(beg_points_ab, beg_points_bc, beg_points_cd)

        # Wire winding

        winding_current_angle = beg_angle
        winding_current_v = winding_offset_v
        winding_points = []
        for _ in range(0, winding_steps):
            position = np.array([
                math.cos(winding_current_angle) * (winding_radius + wire_radius),
                math.sin(winding_current_angle) * (winding_radius + wire_radius),
                winding_current_v
            ])
            winding_current_angle += winding_step_ang
            winding_current_v += winding_step_v
            winding_points.append(position)

        # Bottom end of wire to the contact

        mirror = lambda x: x * np.array([-1.0, 1.0, 1.0])
        end_point_a = mirror(beg_point_a)
        end_tension_ab = mirror(beg_tension_ab)
        end_tension_ba = mirror(beg_tension_ba)
        end_point_b = mirror(beg_point_b)

        end_point_c = mirror(beg_point_c)
        end_tension_cd = np.array([0.0, 0.0, winding_height])
        end_tension_dc = np.array([
            -math.sin(end_angle) * wire_roundness,
            math.cos(end_angle) * wire_roundness,
            0.0
        ])
        end_point_d = np.array([
            math.cos(end_angle) * (winding_radius + wire_radius),
            math.sin(end_angle) * (winding_radius + wire_radius),
            winding_offset_v + winding_height
        ])

        end_curve_dc = curves.Bezier(end_point_d, end_tension_dc, end_point_c, end_tension_cd,
                                     arc_segments * 2)
        end_curve_cb = curves.Line(end_point_c, end_point_b, 1)
        end_curve_ba = curves.Bezier(end_point_b, end_tension_ba, end_point_a, end_tension_ab,
                                     arc_segments)

        end_points_dc = end_curve_dc.tessellate()
        end_points_cb = end_curve_cb.tessellate()
        end_points_ba = end_curve_ba.tessellate()
        end_points = curves.connect_paths(end_points_dc, end_points_cb, end_points_ba)

        # Full wire path

        path_points = curves.connect_paths(beg_points, winding_points, end_points)
        path_points[0] = np.array([*path_points[0][:2], path_points[1][2]])
        path_points[-1] = np.array([*path_points[-1][:2], path_points[-2][2]])

        shape_points = primitives.make_circle_outline(np.zeros(3), wire_radius,
                                                      wire_segments)
        shape_points.reverse()
        shape_points.append(shape_points[0])

        return curves.loft(path=path_points, shape=shape_points)

        # slices = curves.loft(path=path_points, shape=shape_points)

        # slice_transform = model.Transform(matrix=model.rpy_to_matrix((0.0, math.pi / 2.0, 0.0)))
        # slice_transform.translate(beg_point_a)
        # first_slice = [slice_transform.apply(point) for point in shape_points]

        # last_slice_center = model.calc_center_point(slices[-1])
        # slice_transform = model.Transform()
        # slice_transform.translate(-last_slice_center)
        # last_slice = [slice_transform.apply(point) for point in slices[-1]]

        # last_slice_box = model.calc_bounding_box(last_slice)
        # angle = math.atan2((last_slice_box[1][0] - last_slice_box[0][0]),
        #                    (last_slice_box[1][2] - last_slice_box[0][2]))

        # slice_transform = model.Transform()
        # slice_transform.rotate((0.0, 1.0, 0.0), -angle)
        # slice_transform.translate(mirror(beg_point_a))
        #     # + np.array([0.0, 0.0, chamfer / 4.0])) # XXX Fix z offset
        # last_slice = [slice_transform.apply(point) for point in last_slice]

        # return [first_slice] + slices[1:-1] + [last_slice]

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(np.array(descriptor['body']['size']))
        body_radius = max(body_size[0], body_size[1]) / 2.0
        disc_bevel_height = abs(body_size[1] - body_size[0]) / 2.0
        disc_thickness = body_size[2] / 6.0
        inner_radius = body_radius * 0.6
        wire_diameter = primitives.hmils(descriptor['wire']['diameter'])
        hole_radius = wire_diameter
        hole_depth = hole_radius * 2.0
        pin_height = wire_diameter - self.DEFAULT_CHAMFER / 2.0

        body, left_contact = self.make_inductor_body(
            body_radius=body_radius,
            body_height=body_size[2],
            disc_thickness=disc_thickness,
            disc_bevel_height=disc_bevel_height,
            pin_height=pin_height,
            inner_radius=inner_radius,
            hole_radius=hole_radius,
            chamfer=self.DEFAULT_CHAMFER,
            line_segments=resolutions['line'],
            arc_segments=resolutions['arc'],
            corner_segments=resolutions['edge'],
            circle_segments=resolutions['circle']
        )
        body.appearance().material = materials['Inductor.Ferrite']
        left_contact.appearance().material = materials['Inductor.Lead']

        right_contact = copy.deepcopy(left_contact)
        right_contact.rotate(np.array([0.0, 0.0, 1.0]), math.pi)
        right_contact.rename()

        wire = self.make_inductor_wire(
            body_radius=body_radius,
            body_height=body_size[2],
            disc_thickness=disc_thickness,
            pin_height=pin_height,
            wire_radius=wire_diameter / 2.0,
            winding_radius=inner_radius,
            hole_radius=hole_radius,
            hole_depth=hole_depth,
            chamfer=self.DEFAULT_CHAMFER,
            arc_segments=resolutions['arc'],
            circle_segments=resolutions['circle'],
            wire_segments=resolutions['wire']
        )
        wire_mesh = geometry.build_loft_mesh(wire, False, False)
        wire_mesh.appearance().material = materials['Inductor.Copper']
        wire_mesh.optimize()

        return [body, left_contact, right_contact, wire_mesh]


types = [ChipOpenDrumInductor]
