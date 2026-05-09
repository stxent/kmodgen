#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy as np

import bezier
import primitives
from packages import generic
from wrlconv import curves
from wrlconv import model


class Chip(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(Chip.PIVOT_BOUNDING_BOX_CENTER)


class DPAK:
    BODY_CHAMFER = primitives.hmils(0.1)
    BODY_SLOPE_PAD = np.deg2rad(5.0)
    BODY_SLOPE_PIN = np.deg2rad(10.0)
    PIN_SLOPE = np.deg2rad(30.0)


    class PinDesc:
        def __init__(self, pattern, slope=None, descriptor=None):
            if pattern is None and descriptor is None:
                # Not enough information
                raise ValueError()

            if pattern is not None:
                self.length = pattern.length
                self.planar_offset = pattern.planar_offset
                self.vertical_offset = pattern.vertical_offset
                self.shape = pattern.shape
                self.flat = pattern.flat

            if descriptor is not None:
                if 'flat' in descriptor:
                    self.flat = descriptor['flat']
                else:
                    self.flat = False
                if 'length' in descriptor:
                    self.length = primitives.hmils(descriptor['length'])
                if 'shape' in descriptor:
                    self.shape = primitives.hmils(descriptor['shape'])
                    self.planar_offset = -abs((self.shape[1] / 2.0) * math.sin(slope))
                    self.vertical_offset = (self.shape[1] / 2.0) * math.cos(slope)
                self.length -= self.planar_offset

        def __hash__(self):
            return hash((self.length, *self.shape))

        @classmethod
        def make_pattern(cls, slope, descriptor):
            if slope is None or descriptor is None:
                raise ValueError()
            return cls(None, slope, descriptor)

    @staticmethod
    def generate_body(body_chamfer, body_size, pin_height, pad_offset, pad_roundness, pad_size,
                      edge_resolution, line_resolution):
        pad_slope_bot = math.tan(DPAK.BODY_SLOPE_PAD) * pad_size[2]
        pad_slope_top = math.tan(DPAK.BODY_SLOPE_PAD) * body_size[2]
        pin_slope_bot = math.tan(DPAK.BODY_SLOPE_PIN) * pin_height
        pin_slope_top = math.tan(DPAK.BODY_SLOPE_PIN) * (body_size[2] - pin_height)

        x, y = np.array(body_size[:2]) / 2.0
        x_pad = pad_size[0] / 2.0
        y_pad_bot = pad_offset - pad_size[1] / 2.0
        y_pad_top = pad_offset + pad_size[1] / 2.0
        z = body_size[2]
        z_pad = pad_size[2]
        r_pad = pad_roundness

        vertices = [
            # Bottom layer

            # Offset 0
            np.array([-x,              y,                 0.0]),
            np.array([-x_pad,          y,                 0.0]),
            np.array([-x_pad,          y_pad_top - r_pad, 0.0]),
            np.array([-x_pad + r_pad,  y_pad_top,         0.0]),
            # Offset 4
            np.array([ x_pad - r_pad,  y_pad_top,         0.0]),
            np.array([ x_pad,          y_pad_top - r_pad, 0.0]),
            np.array([ x_pad,          y,                 0.0]),
            np.array([ x,              y,                 0.0]),
            np.array([ x,             -y + pin_slope_bot, 0.0]),
            np.array([-x,             -y + pin_slope_bot, 0.0]),
            # Offset 10
            np.array([-x_pad + body_chamfer, y_pad_bot, 0.0]),
            np.array([ x_pad - body_chamfer, y_pad_bot, 0.0]),

            # Middle layer

            # Offset 12
            np.array([-x,              y - pad_slope_bot, z_pad]),
            np.array([-x_pad,          y - pad_slope_bot, z_pad]),
            np.array([-x_pad,          y_pad_top - r_pad, z_pad]),
            np.array([-x_pad + r_pad,  y_pad_top,         z_pad]),
            # Offset 16
            np.array([ x_pad - r_pad,  y_pad_top,         z_pad]),
            np.array([ x_pad,          y_pad_top - r_pad, z_pad]),
            np.array([ x_pad,          y - pad_slope_bot, z_pad]),
            np.array([ x,              y - pad_slope_bot, z_pad]),
            np.array([ x,             -y,                 pin_height]),
            np.array([-x,             -y,                 pin_height]),

            # Top layer

            # Offset 22
            np.array([-x,      y - pad_slope_top, z]),
            np.array([-x_pad,  y - pad_slope_top, z]),
            np.array([ x_pad,  y - pad_slope_top, z]),
            np.array([ x,      y - pad_slope_top, z]),
            # Offset 26
            np.array([ x,     -y + pin_slope_top, z]),
            np.array([-x,     -y + pin_slope_top, z])
        ]

        vertex_attributes = {
            13: {bezier.INVERSION: True},
            18: {bezier.INVERSION: True},
            22: {bezier.CHAMFER: {27: body_chamfer * 2.0, 12: body_chamfer * 2.0}},
            25: {bezier.CHAMFER: {26: body_chamfer * 2.0, 19: body_chamfer * 2.0}},
            26: {bezier.CHAMFER: {25: body_chamfer * 2.0, 20: body_chamfer * 2.0}},
            27: {bezier.CHAMFER: {22: body_chamfer * 2.0, 21: body_chamfer * 2.0}}
        }

        body_faces, lead_faces = [], []

        # Bottom plane
        lead_faces.extend([[2, 3, 4, 5], [2, 5, 6, 1], [1, 6, 11, 10], ])
        body_faces.extend([[0, 1, 10, 9], [6, 7, 8, 11], [10, 11, 8, 9]])

        # Lower side vertical faces
        lead_faces.extend([
            [13, 14, 2, 1], [14, 15, 3, 2], [15, 16, 4, 3], [16, 17, 5, 4], [17, 18, 6, 5]
        ])
        body_faces.extend([
            [12, 13, 1, 0], [18, 19, 7, 6], [19, 20, 8, 7], [20, 21, 9, 8], [21, 12, 0, 9]
        ])

        # Middle plane
        lead_faces.extend([[17, 16, 15, 14], [13, 18, 17, 14]])

        # Upper side vertical faces
        body_faces.extend([
            [12, 22, 23, 13],
            [24, 25, 19, 18],
            [23, 24, 18, 13],
            [12, 21, 27, 22],
            [25, 26, 20, 19],
            [26, 27, 21, 20]
        ])

        # Top plane
        body_faces.extend([[27, 23, 22], [26, 25, 24], [27, 26, 24, 23]])

        lead_vertex_attributes = copy.deepcopy(vertex_attributes)
        lead_vertices = bezier.primitives_to_vertices(lead_faces)
        for i in set(range(len(vertices))).difference(lead_vertices):
            if i not in lead_vertex_attributes:
                lead_vertex_attributes[i] = {}
            lead_vertex_attributes[i][bezier.DISCARD] = True
        for i in (1, 6, 13, 18):
            if i not in lead_vertex_attributes:
                lead_vertex_attributes[i] = {}
            lead_vertex_attributes[i][bezier.HIDDEN] = True

        body_vertex_attributes = copy.deepcopy(vertex_attributes)
        body_vertices = bezier.primitives_to_vertices(body_faces)
        for i in set(range(len(vertices))).difference(body_vertices):
            if i not in body_vertex_attributes:
                body_vertex_attributes[i] = {}
            body_vertex_attributes[i][bezier.DISCARD] = True

        edges = bezier.unpack_faces(body_faces + lead_faces)
        body_edge_attributes = {
            (1, 13): {bezier.INVERSION: True},
            (6, 18): {bezier.INVERSION: True},
            (13, 18): {bezier.INVERSION: True}
        }
        lead_edge_attributes = {
            (1, 13): {bezier.HIDDEN: True},
            (6, 18): {bezier.HIDDEN: True},
            (13, 18): {bezier.HIDDEN: True}
        }

        body = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=body_faces,
            chamfer=body_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=body_vertex_attributes,
            edge_attributes=body_edge_attributes
        )
        lead = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=lead_faces,
            chamfer=body_chamfer,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            vertex_attributes=lead_vertex_attributes,
            edge_attributes=lead_edge_attributes
        )

        return (bezier.patch_to_mesh(body.build()), bezier.patch_to_mesh(lead.build()))

    @staticmethod
    def generate_pins(body_size, body_chamfer, pin_count, pin_height, pin_pitch,
                      materials, resolutions, descriptor):
        try:
            pin_pattern = DPAK.PinDesc.make_pattern(DPAK.BODY_SLOPE_PIN,
                                                    descriptor['pins']['default'])
        except KeyError:
            pin_pattern = None
        try:
            stub_pattern = DPAK.PinDesc.make_pattern(DPAK.BODY_SLOPE_PIN,
                                                     descriptor['pins']['stub'])
        except KeyError:
            stub_pattern = None

        pin_entries = {}
        for i in range(1, pin_count + 1):
            entry = None
            key = str(i)

            try:
                if descriptor['pins'][key] is not None:
                    entry = DPAK.PinDesc(pin_pattern, DPAK.BODY_SLOPE_PIN, descriptor['pins'][key])
                else:
                    entry = DPAK.PinDesc(stub_pattern)
            except KeyError:
                entry = DPAK.PinDesc(pin_pattern)

            if entry is not None:
                pin_entries[i] = entry
        pin_groups = set(pin_entries.values())
        pin_group_meshes = {}

        for group in pin_groups:
            if group.flat:
                mesh = primitives.make_pin_stub(
                    pin_shape_size=group.shape,
                    pin_length=group.length,
                    pin_offset=pin_height + group.vertical_offset,
                    end_slope=DPAK.BODY_SLOPE_PIN,
                    edge_resolution=resolutions['chamfer'],
                    line_resolution=resolutions['line']
                )
            else:
                mesh = primitives.make_pin_mesh(
                    pin_shape_size=group.shape,
                    pin_height=pin_height + group.vertical_offset,
                    pin_length=group.length,
                    pin_slope=DPAK.PIN_SLOPE,
                    end_slope=DPAK.BODY_SLOPE_PIN,
                    edge_resolution=resolutions['chamfer'],
                    line_resolution=resolutions['line'],
                    slope_resolution=resolutions['edge']
                )

            if 'DPAK.Lead' in materials:
                mesh.appearance().material = materials['DPAK.Lead']
            pin_group_meshes[hash(group)] = mesh

        return DPAK.generate_pin_rows(
            count=pin_count,
            size=body_size[:2],
            pitch=pin_pitch,
            patterns=pin_group_meshes,
            entries=pin_entries
        )

    @staticmethod
    def generate_pin_rows(count, size, pitch, patterns, entries):
        def make_pin(mesh, position, number):
            pin = model.Mesh(parent=mesh, name='Pin{:d}'.format(number))
            pin.translate([position[0], position[1], 0.0])
            pin.rotate([0.0, 0.0, 1.0], -math.pi / 2.0)
            return pin

        first_pin_offset = pitch * (count - 1) / 2.0
        y_offset = size[1] / 2.0

        meshes = []
        for i in range(1, count + 1):
            x_offset = pitch * (i - 1) - first_pin_offset

            if i in entries:
                entry = entries[i]
                mesh = patterns[hash(entry)]
                meshes.append(make_pin(mesh,
                                       np.array([-x_offset, -(y_offset + entry.planar_offset)]), i))

        return meshes

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(descriptor['body']['size'])
        heatsink_size = primitives.hmils(descriptor['pins']['heatsink']['size'])
        heatsink_offset = primitives.hmils(descriptor['pins']['heatsink']['offset'])
        pin_count = descriptor['pins']['count']
        pin_height = body_size[2] / 2.0
        pin_pitch = primitives.hmils(descriptor['pins']['pitch'])

        body_meshes = DPAK.generate_body(
            body_chamfer=DPAK.BODY_CHAMFER,
            body_size=body_size,
            pin_height=pin_height,
            pad_offset=heatsink_offset[1],
            pad_roundness=(heatsink_offset[1] - (body_size[1] - heatsink_size[1]) / 2.0) / 2.0,
            pad_size=heatsink_size,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        if 'DPAK.Plastic' in materials:
            body_meshes[0].appearance().material = materials['DPAK.Plastic']
        if 'DPAK.Lead' in materials:
            body_meshes[1].appearance().material = materials['DPAK.Lead']

        pin_meshes = DPAK.generate_pins(
            body_size=body_size,
            body_chamfer=DPAK.BODY_CHAMFER,
            pin_count=pin_count,
            pin_height=pin_height,
            pin_pitch=pin_pitch,
            materials=materials,
            resolutions=resolutions,
            descriptor=descriptor
        )
        return list(body_meshes) + pin_meshes


class SOT:
    BODY_CHAMFER = primitives.hmils(0.05)
    BODY_OFFSET_Z = primitives.hmils(0.1)
    BODY_SLOPE = 10.0
    PIN_SLOPE = 5.0

    MARK_MARGIN = primitives.hmils(0.4)
    MARK_RADIUS = primitives.hmils(0.2)


    class PinDesc:
        def __init__(self, pattern, slope=None, descriptor=None):
            if pattern is None and descriptor is None:
                # Not enough information
                raise ValueError()

            if pattern is not None:
                self.length = pattern.length
                self.planar_offset = pattern.planar_offset
                self.vertical_offset = pattern.vertical_offset
                self.shape = pattern.shape

            if descriptor is not None:
                if 'length' in descriptor:
                    self.length = primitives.hmils(descriptor['length'])
                if 'shape' in descriptor:
                    self.shape = primitives.hmils(descriptor['shape'])
                    self.planar_offset = -abs((self.shape[1] / 2.0) * math.sin(slope))
                    self.vertical_offset = (self.shape[1] / 2.0) * math.cos(slope)
                self.length -= self.planar_offset

        def __hash__(self):
            return hash((self.length, *self.shape))

        @classmethod
        def make_pattern(cls, slope, descriptor):
            if slope is None or descriptor is None:
                raise ValueError()
            return cls(None, slope, descriptor)


    def __init__(self, material='SOT'):
        self.material = material

    @staticmethod
    def detach_body_strip(mesh, size, chamfer, strip_width, epsilon=1e-6):
        detach_region = (
            (
                -size[0] / 2.0 + chamfer - epsilon,
                -size[1] / 2.0 + chamfer - epsilon,
                size[2] / 2.0 - epsilon
            ), (
                size[0] / 2.0 - chamfer + epsilon,
                -size[1] / 2.0 + chamfer + strip_width + epsilon,
                size[2] / 2.0 + epsilon
            )
        )

        return mesh.detach_faces([detach_region])

    @staticmethod
    def move_body_strip(mesh, size, chamfer, strip_width, epsilon=1e-6):
        region = (
            (-size[0] / 2.0 - chamfer - epsilon, -epsilon, size[2] / 2.0 - chamfer - epsilon),
            ( size[0] / 2.0 + chamfer + epsilon,  epsilon, size[2] / 2.0 + epsilon),
            1
        )

        transform = model.Transform()
        transform.translate(np.array([0.0, -(size[1] / 2.0 - chamfer - strip_width), 0.0]))

        result = model.AttributedMesh(name='Body', regions=[region])
        result.append(mesh)
        result.apply_transform({1: transform})
        return result

    def generate_body(self, body_size, body_chamfer, band_offset, band_size, is_band_inverted,
                      is_pin_flat, materials, resolutions, descriptor):
        try:
            strip_width = body_size[1] / 10.0 if descriptor['mark']['strip'] else None
        except KeyError:
            strip_width = None

        if strip_width is None:
            try:
                dot_radius = SOT.MARK_RADIUS if descriptor['mark']['dot'] else None
            except KeyError:
                dot_radius = None
            body_resolutions = resolutions['line']
        else:
            body_resolutions = (resolutions['line'], 2, resolutions['line'])
            dot_radius = None

        dot_offset_xy = -(body_size[:2] / 2.0 - SOT.MARK_MARGIN)
        dot_offset = np.array([*dot_offset_xy, 0.0])

        body_offset_z = body_size[2] / 2.0
        if not is_pin_flat:
            body_offset_z += SOT.BODY_OFFSET_Z

        meshes = []

        box_meshes = primitives.make_box_with_mark(
            size=body_size,
            chamfer=body_chamfer,
            edge_resolution=resolutions['edge'],
            line_resolution=body_resolutions,
            plane_resolution=max(resolutions['line'], 2),
            band_size=band_size,
            band_offset=band_offset,
            mark_radius=dot_radius,
            mark_offset=dot_offset,
            mark_resolution=resolutions['circle']
        )
        try:
            body_mesh = box_meshes[0]
            dot_mesh = box_meshes[1]
        except TypeError:
            body_mesh = box_meshes
            dot_mesh = None

        if strip_width is not None:
            body_mesh = SOT.move_body_strip(body_mesh, body_size, body_chamfer, strip_width)
            strip_mesh = SOT.detach_body_strip(body_mesh, body_size, body_chamfer, strip_width)

            if f'{self.material}.Mark' in materials:
                strip_mesh.appearance().material = materials[f'{self.material}.Mark']
            strip_mesh.rename('Mark')
            strip_mesh.translate(np.array([0.0, 0.0, body_offset_z]))
            meshes.append(strip_mesh)

        if f'{self.material}.Plastic' in materials:
            body_mesh.appearance().material = materials[f'{self.material}.Plastic']
        body_mesh.rename('Body')
        body_mesh.translate(np.array([0.0, 0.0, body_offset_z]))
        meshes.append(body_mesh)

        if dot_mesh is not None:
            dot_mesh.translate(np.array([0.0, 0.0, body_offset_z]))

            if f'{self.material}.Mark' in materials:
                dot_mesh.appearance().material = materials[f'{self.material}.Mark']
            dot_mesh.rename('Mark')
            meshes.append(dot_mesh)

        # Special case for packages with two pins: match orientation for Chip footprints
        if descriptor['pins']['count'] == 2:
            for mesh in meshes:
                mesh.rotate((0.0, 0.0, 1.0), -math.pi / 2.0)

        return meshes

    def generate_pins(self, body_size, body_chamfer, band_offset, band_size,
                      is_band_inverted, is_pin_flat, materials, resolutions, descriptor):
        body_slope = np.deg2rad(SOT.BODY_SLOPE)
        if is_band_inverted:
            body_slope = -body_slope

        try:
            pin_pitch = primitives.hmils(descriptor['pins']['pitch'])
        except KeyError:
            pin_pitch = 0.0
        try:
            pin_slope = np.deg2rad(descriptor['pins']['slope'])
        except KeyError:
            pin_slope = np.deg2rad(SOT.PIN_SLOPE)

        if is_pin_flat:
            pin_height = body_size[2] / 2.0 + band_offset
        else:
            pin_height = body_size[2] / 2.0 + band_offset + SOT.BODY_OFFSET_Z

        try:
            pin_pattern = SOT.PinDesc.make_pattern(body_slope, descriptor['pins']['default'])
        except KeyError:
            pin_pattern = None

        pin_entries = {}
        for i in range(1, descriptor['pins']['count'] + 1):
            entry = None
            key = str(i)

            try:
                if descriptor['pins'][key] is not None:
                    entry = SOT.PinDesc(pin_pattern, body_slope, descriptor['pins'][key])
            except KeyError:
                entry = SOT.PinDesc(pin_pattern)

            if entry is not None:
                if entry.shape[1] + body_chamfer > band_offset + body_size[2] / 2.0:
                    raise ValueError
                pin_entries[i] = entry
        pin_groups = set(pin_entries.values())
        pin_group_meshes = {}

        for group in pin_groups:
            if is_pin_flat:
                mesh = primitives.make_flat_pin_mesh(
                    pin_shape_size=group.shape,
                    pin_height=pin_height - group.vertical_offset,
                    pin_length=group.length,
                    end_slope=body_slope,
                    edge_resolution=resolutions['chamfer'],
                    line_resolution=resolutions['line'],
                    slope_resolution=resolutions['edge']
                )
            else:
                mesh = primitives.make_pin_mesh(
                    pin_shape_size=group.shape,
                    pin_height=pin_height + group.vertical_offset,
                    pin_length=group.length,
                    pin_slope=pin_slope,
                    end_slope=body_slope,
                    edge_resolution=resolutions['chamfer'],
                    line_resolution=resolutions['line'],
                    slope_resolution=resolutions['edge']
                )

            if f'{self.material}.Lead' in materials:
                mesh.appearance().material = materials[f'{self.material}.Lead']

            pin_group_meshes[hash(group)] = mesh

        return SOT.generate_pin_rows(
            count=descriptor['pins']['count'],
            size=body_size[:2] + band_size * 2.0,
            pitch=pin_pitch,
            patterns=pin_group_meshes,
            entries=pin_entries
        )

    @staticmethod
    def generate_pin_rows(count, size, pitch, patterns, entries):
        def make_pin(mesh, position, angle, number, swap_xy):
            pin = model.Mesh(parent=mesh, name='Pin{:d}'.format(number))
            if swap_xy:
                pin.translate([position[1], position[0], 0.0])
                pin.rotate([0.0, 0.0, 1.0], angle - math.pi)
            else:
                pin.translate([position[0], position[1], 0.0])
                pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        columns = count // 2
        swap_xy = count == 2
        first_pin_offset = pitch * (columns - 1) / 2.0
        y_offset = size[1] / 2.0

        meshes = []
        for i in range(1, columns + 1):
            x_offset = pitch * (i - 1) - first_pin_offset

            if i + columns in entries:
                entry = entries[i + columns]
                mesh = patterns[hash(entry)]
                meshes.append(make_pin(mesh,
                                       np.array([x_offset, y_offset + entry.planar_offset]),
                                       math.pi, i + columns, swap_xy))

            if i in entries:
                entry = entries[i]
                mesh = patterns[hash(entry)]
                meshes.append(make_pin(mesh,
                                       np.array([-x_offset, -(y_offset + entry.planar_offset)]),
                                       0.0, i, swap_xy))

        return meshes

    def generate(self, materials, resolutions, _, descriptor):
        try:
            is_pin_flat = descriptor['pins']['flat']
        except KeyError:
            is_pin_flat = False
        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0
        try:
            is_band_inverted = descriptor['band']['inverse']
        except KeyError:
            is_band_inverted = is_pin_flat

        body_chamfer = SOT.BODY_CHAMFER
        body_size = primitives.hmils(descriptor['body']['size'])
        partial_heights = (
            body_size[2] / 2.0 + band_offset,
            body_size[2] / 2.0 - band_offset
        )
        band_size = math.tan(np.deg2rad(SOT.BODY_SLOPE)) * min(partial_heights)
        body_size = np.array([
            body_size[0] - band_size * 2.0,
            body_size[1] - band_size * 2.0,
            body_size[2]
        ])

        # Special case for packages with two pins: match orientation for Chip footprints
        if descriptor['pins']['count'] == 2:
            body_size[0], body_size[1] = body_size[1], body_size[0]

        body_meshes = self.generate_body(
            body_size=body_size,
            body_chamfer=SOT.BODY_CHAMFER,
            band_offset=band_offset,
            band_size=band_size,
            is_band_inverted=is_band_inverted,
            is_pin_flat=is_pin_flat,
            materials=materials,
            resolutions=resolutions,
            descriptor=descriptor
        )
        pin_meshes = self.generate_pins(
            body_size=body_size,
            body_chamfer=SOT.BODY_CHAMFER,
            band_offset=band_offset,
            band_size=band_size,
            is_band_inverted=is_band_inverted,
            is_pin_flat=is_pin_flat,
            materials=materials,
            resolutions=resolutions,
            descriptor=descriptor
        )
        return body_meshes + pin_meshes


class SOD(SOT):
    def __init__(self):
        super().__init__('SOD')


types = [
    Chip,
    DPAK,
    SOD,
    SOT
]
