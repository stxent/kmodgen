#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# qfn.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

from wrlconv import geometry
from wrlconv import model
import primitives


class QFN:
    BODY_CHAMFER = primitives.hmils(0.05)
    MARK_RADIUS  = primitives.hmils(0.5)

    CHAMFER_RESOLUTION = 2
    LINE_RESOLUTION    = 1
    MARK_RESOLUTION    = 24

    @staticmethod
    def blow_top_vertices(mesh, size, band, chamfer):
        src_plane_size = size[0:2] - 2.0 * chamfer / math.sqrt(2.0) - 4.0 * band[0:2]
        dst_plane_size = size[0:2] - 2.0 * (chamfer + chamfer / math.sqrt(2.0))
        region = (
            (-src_plane_size[0] / 2.0, -src_plane_size[1] / 2.0,     0.0),
            ( src_plane_size[0] / 2.0,  src_plane_size[1] / 2.0, size[2]),
            1
        )

        transform = model.Transform()
        transform.scale(numpy.array([
            dst_plane_size[0] / src_plane_size[0],
            dst_plane_size[1] / src_plane_size[1],
            1.0
        ]))

        result = model.AttributedMesh(name='Body', regions=[region])
        result.append(mesh)
        result.apply_transform({1: transform})
        return result

    # @staticmethod
    def detach_pads(mesh, count, size, band, pin_width, pin_pitch, first_pin_offset):
        detach_regions = []
        for i in range(0, count[0]):
            x_pos = i * pin_pitch - first_pin_offset[0]
            y_pos = size[1] / 2.0

            detach_regions.append((
                (x_pos - pin_width / 2.0,              0.0, -size[2]),
                (x_pos + pin_width / 2.0,  y_pos + band[1],      0.0)
            ))
            detach_regions.append((
                (x_pos - pin_width / 2.0, -y_pos - band[1], -size[2]),
                (x_pos + pin_width / 2.0,              0.0,      0.0)
            ))
        for i in range(0, count[1]):
            x_pos = size[0] / 2.0
            y_pos = i * pin_pitch - first_pin_offset[1]

            detach_regions.append((
                (             0.0, y_pos - pin_width / 2.0, -size[2]),
                ( x_pos + band[0], y_pos + pin_width / 2.0,      0.0)
            ))
            detach_regions.append((
                (-x_pos - band[0], y_pos - pin_width / 2.0, -size[2]),
                (             0.0, y_pos + pin_width / 2.0,      0.0)
            ))
        return mesh.detach_faces(detach_regions)

    @staticmethod
    def fix_inner_corners(mesh, count, size, band, pin_length, chamfer):
        x_pos = size[0] / 2.0 - band[0] * 2.0 - chamfer / math.sqrt(2.0)
        y_pos = size[1] / 2.0 - band[1] * 2.0 - chamfer / math.sqrt(2.0)

        regions = [
            (( x_pos,  y_pos, -size[2]), ( x_pos,  y_pos, 0.0), 1),
            ((-x_pos,  y_pos, -size[2]), (-x_pos,  y_pos, 0.0), 1),
            ((-x_pos, -y_pos, -size[2]), (-x_pos, -y_pos, 0.0), 1),
            (( x_pos, -y_pos, -size[2]), ( x_pos, -y_pos, 0.0), 1)
        ]

        if count[1] == 0:
            pin_border_x = size[0] / 2.0 - chamfer / math.sqrt(2.0) - chamfer
        else:
            pin_border_x = size[0] / 2.0 - pin_length

        if count[0] == 0:
            pin_border_y = size[1] / 2.0 - chamfer / math.sqrt(2.0) - chamfer
        else:
            pin_border_y = size[1] / 2.0 - pin_length

        transform = model.Transform()
        transform.scale(numpy.array([
            pin_border_x / x_pos,
            pin_border_y / y_pos,
            1.0
        ]))

        result = model.AttributedMesh(name='Body', regions=regions)
        result.append(mesh)
        result.apply_transform({1: transform})
        return result

    @staticmethod
    def make_bottom_plane(mesh, size, chamfer):
        region = (
            (-size[0] / 2.0 + chamfer, -size[1] / 2.0 + chamfer, -size[2]),
            ( size[0] / 2.0 - chamfer,  size[1] / 2.0 - chamfer,      0.0)
        )
        body_vertices = mesh.find_vertices([region])
        primitives.append_solid_cap(mesh, body_vertices, normal=numpy.array([0.0, 0.0, -1.0]))

    @staticmethod
    def make_top_plane(mesh, size, chamfer):
        plane_size = size[0:2] - 2.0 * (chamfer + chamfer / math.sqrt(2.0))
        region = (
            (-plane_size[0] / 2.0, -plane_size[1] / 2.0,     0.0),
            ( plane_size[0] / 2.0,  plane_size[1] / 2.0, size[2])
        )
        body_vertices = mesh.find_vertices([region])
        primitives.append_solid_cap(mesh, body_vertices, normal=numpy.array([0.0, 0.0, 1.0]))

    @staticmethod
    def make_heatsink_hole(mesh, body_size, heatsink_size, chamfer):
        region = (
            (-body_size[0] / 2.0 + chamfer, -body_size[1] / 2.0 + chamfer, -body_size[2]),
            ( body_size[0] / 2.0 - chamfer,  body_size[1] / 2.0 - chamfer,           0.0)
        )
        heatsink_corners = [
            numpy.array([ heatsink_size[0] / 2.0,  heatsink_size[1] / 2.0, -body_size[2] / 2.0]),
            numpy.array([-heatsink_size[0] / 2.0,  heatsink_size[1] / 2.0, -body_size[2] / 2.0]),
            numpy.array([-heatsink_size[0] / 2.0, -heatsink_size[1] / 2.0, -body_size[2] / 2.0]),
            numpy.array([ heatsink_size[0] / 2.0, -heatsink_size[1] / 2.0, -body_size[2] / 2.0])
        ]
        heatsink_vertices = geometry.make_bezier_quad_outline(heatsink_corners)
        body_vertices = mesh.find_vertices([region])
        primitives.append_hollow_cap(mesh, body_vertices, heatsink_vertices,
                                    numpy.array([0.0, 0.0, -1.0]))

    @staticmethod
    def make_mark_hole(mesh, body_size, mark_radius, mark_offset, chamfer, resolution):
        plane_size = body_size[0:2] - 2.0 * (chamfer + chamfer / math.sqrt(2.0))
        region = (
            (-plane_size[0] / 2.0, -plane_size[1] / 2.0,          0.0),
            ( plane_size[0] / 2.0,  plane_size[1] / 2.0, body_size[2])
        )
        mark_vertices = geometry.make_circle_outline(
            numpy.array([*mark_offset, body_size[2] / 2.0]),
            mark_radius, resolution
        )
        body_vertices = mesh.find_vertices([region])
        primitives.append_hollow_cap(mesh, body_vertices, mark_vertices,
                                     normal=numpy.array([0.0, 0.0, 1.0]))

    @staticmethod
    def mold_edge_pin_offsets(mesh, size, pin_width, pin_pitch, band, plane_size, resolution,
                              chamfer, first_pin_offset):
        counter = 1
        regions = []
        transforms = {}

        for i in range(2, resolution[0] - 1):
            x_pin_num = (i - 2) // 2
            x_pin_off = -pin_width / 2.0 if i & 1 == 0 else pin_width / 2.0
            x_pin = x_pin_num * pin_pitch + x_pin_off - first_pin_offset[0]

            x_pos = (i * plane_size[0]) / resolution[0] - plane_size[0] / 2.0
            y_pos = size[1] / 2.0

            transform = model.Transform()
            transform.translate(numpy.array([x_pin - x_pos, 0.0, 0.0]))

            regions.append((
                (x_pos - band[0], y_pos - band[1] * 3.0, -size[2]),
                (x_pos + band[0], y_pos + band[1],        size[2]),
                counter
            ))
            transforms[counter] = transform
            counter += 1

            regions.append((
                (x_pos - band[0], -y_pos - band[1],       -size[2]),
                (x_pos + band[0], -y_pos + band[1] * 3.0,  size[2]),
                counter
            ))
            transforms[counter] = transform
            counter += 1

        # Horizontal side vertices
        x_vertex_offset = plane_size[0] / 2.0 - band[0] * 2.0
        # x_plane_border = size[0] / 2.0
        # x_pin_border = first_pin_offset[0] + pin_width / 2.0
        x_pin_border = plane_size[0] / 2.0 - chamfer
        # x_pin_delta = (x_plane_border + x_pin_border) / 2.0 - x_vertex_offset
        x_pin_delta = x_pin_border - x_vertex_offset

        regions.append((
            (x_vertex_offset - band[0],  size[1] / 2.0 - band[1], -size[2]),
            (x_vertex_offset + band[0],  size[1] / 2.0 + band[1],  size[2]),
            counter
        ))
        regions.append((
            (x_vertex_offset - band[0], -size[1] / 2.0 - band[1], -size[2]),
            (x_vertex_offset + band[0], -size[1] / 2.0 + band[1],  size[2]),
            counter
        ))
        transform = model.Transform()
        transform.translate(numpy.array([x_pin_delta, 0.0, 0.0]))
        transforms[counter] = transform
        counter += 1

        regions.append((
            (-x_vertex_offset - band[0],  size[1] / 2.0 - band[1], -size[2]),
            (-x_vertex_offset + band[0],  size[1] / 2.0 + band[1],  size[2]),
            counter
        ))
        regions.append((
            (-x_vertex_offset - band[0], -size[1] / 2.0 - band[1], -size[2]),
            (-x_vertex_offset + band[0], -size[1] / 2.0 + band[1],  size[2]),
            counter
        ))
        transform = model.Transform()
        transform.translate(numpy.array([-x_pin_delta, 0.0, 0.0]))
        transforms[counter] = transform
        counter += 1

        for i in range(2, resolution[1] - 1):
            y_pin_num = (i - 2) // 2
            y_pin_off = -pin_width / 2.0 if i & 1 == 0 else pin_width / 2.0
            y_pin = y_pin_num * pin_pitch + y_pin_off - first_pin_offset[1]

            x_pos = size[0] / 2.0
            y_pos = (i * plane_size[1]) / resolution[1] - plane_size[1] / 2.0

            transform = model.Transform()
            transform.translate(numpy.array([0.0, y_pin - y_pos, 0.0]))

            regions.append((
                (x_pos - band[0] * 3.0, y_pos - band[1], -size[2]),
                (x_pos + band[0],       y_pos + band[1],  size[2]),
                counter
            ))
            transforms[counter] = transform
            counter += 1

            regions.append((
                (-x_pos - band[0],       y_pos - band[1], -size[2]),
                (-x_pos + band[0] * 3.0, y_pos + band[1],  size[2]),
                counter
            ))
            transforms[counter] = transform
            counter += 1

        # Vertical side vertices
        y_vertex_offset = plane_size[1] / 2.0 - band[1] * 2.0
        # y_plane_border = size[1] / 2.0
        # y_pin_border = first_pin_offset[1] + pin_width / 2.0
        y_pin_border = plane_size[1] / 2.0 - chamfer
        # y_pin_delta = (y_plane_border + y_pin_border) / 2.0 - y_vertex_offset
        y_pin_delta = y_pin_border - y_vertex_offset

        regions.append((
            ( size[0] / 2.0 - band[0], y_vertex_offset - band[1], -size[2]),
            ( size[0] / 2.0 + band[0], y_vertex_offset + band[1],  size[2]),
            counter
        ))
        regions.append((
            (-size[0] / 2.0 - band[0], y_vertex_offset - band[1], -size[2]),
            (-size[0] / 2.0 + band[0], y_vertex_offset + band[1],  size[2]),
            counter
        ))
        transform = model.Transform()
        transform.translate(numpy.array([0.0, y_pin_delta, 0.0]))
        transforms[counter] = transform
        counter += 1

        regions.append((
            ( size[0] / 2.0 - band[0], -y_vertex_offset - band[1], -size[2]),
            ( size[0] / 2.0 + band[0], -y_vertex_offset + band[1],  size[2]),
            counter
        ))
        regions.append((
            (-size[0] / 2.0 - band[0], -y_vertex_offset - band[1], -size[2]),
            (-size[0] / 2.0 + band[0], -y_vertex_offset + band[1],  size[2]),
            counter
        ))
        transform = model.Transform()
        transform.translate(numpy.array([0.0, -y_pin_delta, 0.0]))
        transforms[counter] = transform
        counter += 1

        result = model.AttributedMesh(name='Body', regions=regions)
        result.append(mesh)
        result.apply_transform(transforms)
        return result

    @staticmethod
    def mold_inner_pin_offsets(mesh, size, band, pin_width, pin_height, pin_length, chamfer,
                               first_pin_offset):
        median_region = ((-size[0], -size[1], -band[2]), (size[0], size[1], band[2]), 1)
        median_transform = model.Transform()
        median_transform.translate(numpy.array([0.0, 0.0, -size[2] / 2.0 + pin_height]))
        inner_regions = [
            (
                (-first_pin_offset[0] - pin_width / 2.0, -size[1] / 2.0 + band[1],       -size[2]),
                ( first_pin_offset[0] + pin_width / 2.0, -size[1] / 2.0 + band[1] * 3.0,      0.0),
                2
            ), (
                (-first_pin_offset[0] - pin_width / 2.0,  size[1] / 2.0 - band[1],       -size[2]),
                ( first_pin_offset[0] + pin_width / 2.0,  size[1] / 2.0 - band[1] * 3.0,      0.0),
                3
            ), (
                (-size[0] / 2.0 + band[0],       -first_pin_offset[1] - pin_width / 2.0, -size[2]),
                (-size[0] / 2.0 + band[0] * 3.0,  first_pin_offset[1] + pin_width / 2.0,      0.0),
                4
            ), (
                ( size[0] / 2.0 - band[0],       -first_pin_offset[1] - pin_width / 2.0, -size[2]),
                ( size[0] / 2.0 - band[0] * 3.0,  first_pin_offset[1] + pin_width / 2.0,      0.0),
                5
            )
        ]
        inner_transform_2 = model.Transform()
        inner_transform_2.translate(numpy.array([0.0,  pin_length - band[1] * 2.0 - chamfer, 0.0]))
        inner_transform_3 = model.Transform()
        inner_transform_3.translate(numpy.array([0.0, -pin_length + band[1] * 2.0 + chamfer, 0.0]))
        inner_transform_4 = model.Transform()
        inner_transform_4.translate(numpy.array([ pin_length - band[0] * 2.0 - chamfer, 0.0, 0.0]))
        inner_transform_5 = model.Transform()
        inner_transform_5.translate(numpy.array([-pin_length + band[0] * 2.0 + chamfer, 0.0, 0.0]))

        result = model.AttributedMesh(name='Body', regions=[median_region] + inner_regions)
        result.append(mesh)
        result.apply_transform({
            1: median_transform,
            2: inner_transform_2,
            3: inner_transform_3,
            4: inner_transform_4,
            5: inner_transform_5
        })
        return result

    @staticmethod
    def remove_unused_vertices(mesh, size, band):
        center_region_bottom = (
            (-size[0] / 2.0 + band[0], -size[1] / 2.0 + band[1], -size[2]),
            ( size[0] / 2.0 - band[0],  size[1] / 2.0 - band[1], 0.0)
        )
        center_region_top = (
            (-size[0] / 2.0 + band[0], -size[1] / 2.0 + band[1], 0.0),
            ( size[0] / 2.0 - band[0],  size[1] / 2.0 - band[1], size[2])
        )
        mesh.detach_faces([center_region_bottom, center_region_top])

    @staticmethod
    def make_qfn_body(size, count, chamfer, pin_pitch, pin_width, pin_height, pin_length,
                      heatsink=None, mark_radius=None, mark_offset=numpy.array([0.0, 0.0]),
                      edge_resolution=3, line_resolution=1, mark_resolution=24):
        chamfer_width = chamfer / math.sqrt(2.0)
        resolution = count * 2 + 3
        first_pin_offset = (numpy.asfarray(count) - 1.0) * pin_pitch / 2.0

        plane_size = size - 2.0 * chamfer_width
        band = numpy.array([
            plane_size[0] / resolution[0] / 2.0,
            plane_size[1] / resolution[1] / 2.0,
            size[2] / 4.0
        ])

        source_mesh = primitives.make_box(size=size, chamfer=chamfer,
                                          edge_resolution=edge_resolution,
                                          line_resolution=(resolution[0], resolution[1], 2))
        QFN.remove_unused_vertices(source_mesh, size, band)

        top_face_forming = QFN.blow_top_vertices(source_mesh, size, band, chamfer)
        edge_pin_forming = QFN.mold_edge_pin_offsets(top_face_forming, size, pin_width, pin_pitch,
                                                     band, plane_size, resolution, chamfer,
                                                     first_pin_offset)
        corner_pin_forming = QFN.fix_inner_corners(edge_pin_forming, count, size, band, pin_length,
                                                   chamfer)
        final_forming = QFN.mold_inner_pin_offsets(corner_pin_forming, size, band, pin_width,
                                                   pin_height, pin_length, chamfer_width,
                                                   first_pin_offset)

        pin_mesh = QFN.detach_pads(final_forming, count, size, band, pin_width, pin_pitch,
                                   first_pin_offset)

        if mark_radius is not None:
            QFN.make_mark_hole(final_forming, size, mark_radius, mark_offset, chamfer,
                               mark_resolution)
            mark_mesh = geometry.Circle(mark_radius, mark_resolution)
            mark_mesh.translate([*mark_offset, size[2] / 2.0])
        else:
            QFN.make_top_plane(final_forming, size, chamfer)
            mark_mesh = None

        if heatsink is not None:
            QFN.make_heatsink_hole(final_forming, size, heatsink, chamfer)

            heatsink_mesh = geometry.Plane(heatsink, (line_resolution, line_resolution))
            heatsink_mesh.translate([0.0, 0.0, -size[2] / 2.0])
            pin_mesh.append(heatsink_mesh)
        else:
            QFN.make_bottom_plane(final_forming, size, chamfer)

        return [final_forming, pin_mesh, mark_mesh]

    def generate(self, materials, _, descriptor):
        try:
            pin_columns, pin_rows = descriptor['pins']['columns'], descriptor['pins']['rows']
        except KeyError:
            pin_columns, pin_rows = descriptor['pins']['count'] // 2, 0
        pin_count = numpy.array([pin_columns, pin_rows])

        body_size = primitives.hmils(descriptor['body']['size'])
        pin_width = primitives.hmils(descriptor['pins']['width'])
        pin_pitch = primitives.hmils(descriptor['pins']['pitch'])
        pin_length = primitives.hmils(descriptor['pins']['length'])

        try:
            mark_dot = primitives.hmils(descriptor['mark']['dot'])
        except:
            mark_dot = True

        if mark_dot:
            try:
                mark_radius = primitives.hmils(descriptor['mark']['radius'])
            except KeyError:
                mark_radius = QFN.MARK_RADIUS
            mark_offset = QFN.calc_mark_offset(body_size, mark_radius, QFN.BODY_CHAMFER)
        else:
            mark_radius = None
            mark_offset = numpy.array([0.0, 0.0])

        try:
            pin_height = primitives.hmils(descriptor['pins']['height'])
        except KeyError:
            pin_height = 0.1 # XXX

        try:
            heatsink_size = primitives.hmils(descriptor['heatsink']['size'])
        except KeyError:
            heatsink_size = None

        body_mesh, pin_mesh, mark_mesh = QFN.make_qfn_body(
            size=body_size,
            count=pin_count,
            chamfer=QFN.BODY_CHAMFER,
            pin_pitch=pin_pitch,
            pin_width=pin_width,
            pin_height=pin_height,
            pin_length=pin_length,
            heatsink=heatsink_size,
            mark_radius=mark_radius,
            mark_offset=mark_offset,
            edge_resolution=QFN.CHAMFER_RESOLUTION,
            line_resolution=QFN.LINE_RESOLUTION,
            mark_resolution=QFN.MARK_RESOLUTION
        )

        meshes = []
        body_transform = model.Transform()
        body_transform.translate([0.0, 0.0, body_size[2] / 2.0])

        if 'Body' in materials:
            body_mesh.appearance().material = materials['Body']
        body_mesh.apply(body_transform)
        body_mesh.rename('Body')
        meshes.append(body_mesh)

        if 'Pin' in materials:
            pin_mesh.appearance().material = materials['Pin']
        pin_mesh.apply(body_transform)
        pin_mesh.rename('Pins')
        meshes.append(pin_mesh)

        if mark_mesh is not None:
            if 'Mark' in materials:
                mark_mesh.appearance().material = materials['Mark']
            mark_mesh.apply(body_transform)
            mark_mesh.rename('Mark')
            meshes.append(mark_mesh)

        return meshes

    @staticmethod
    def calc_mark_offset(size, radius, chamfer):
        plane_size = size[0:2] - 2.0 * chamfer / math.sqrt(2.0)
        return -plane_size / 2.0 + 2.0 * radius


class DFN(QFN):
    pass


class LGA(QFN):
    pass


types = [QFN, DFN, LGA]
