#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy as np

import primitives
from packages import generic
from wrlconv import curves
from wrlconv import geometry
from wrlconv import model


class Chip(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(Chip.PIVOT_BOUNDING_BOX_CENTER)


class MELF:
    def __init__(self):
        pass

    @staticmethod
    def build_band_curves(body_radius, band_length, band_offset, line_resolution):
        band = []

        if band_length > 0.0:
            band.append(curves.Line(
                (band_offset - band_length / 2.0, 0.0, body_radius),
                (band_offset + band_length / 2.0, 0.0, body_radius), line_resolution
            ))

        return [band]

    @staticmethod
    def build_body_curves(length, body_curvature, body_radius, contact_length, band_length,
                          band_offset, edge_resolution, line_resolution):
        weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        left_part, right_part = [], []

        # Left rounded edge
        left_part.append(curves.Bezier(
            (-length / 2.0 + contact_length, 0.0, body_radius - body_curvature),
            (0.0, 0.0, body_curvature * weight),
            (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
            (-body_curvature * weight, 0.0, 0.0),
            edge_resolution
        ))

        if band_length > 0.0:
            # Package glass to the left of the band
            left_part.append(curves.Line(
                (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
                (band_offset - band_length / 2.0, 0.0, body_radius), line_resolution
            ))
            # Package glass to the right of the band
            right_part.append(curves.Line(
                (band_offset + band_length / 2.0, 0.0, body_radius),
                (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
                line_resolution
            ))
        else:
            left_part.append(curves.Line(
                (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
                (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
                line_resolution
            ))

        # Right rounded edge
        right_part.append(curves.Bezier(
            (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
            (body_curvature * weight, 0.0, 0.0),
            (length / 2.0 - contact_length, 0.0, body_radius - body_curvature),
            (0.0, 0.0, body_curvature * weight),
            edge_resolution
        ))

        return [left_part, right_part]

    @staticmethod
    def build_contact_curves(length, body_curvature, body_radius, contact_curvature,
                             contact_length, contact_radius, edge_resolution, line_resolution):
        rotation = model.Transform(matrix=model.make_rotation_matrix(np.array([0.0, 0.0, 1.0]),
            math.pi))
        weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        left_contact = []

        # Left contact
        left_contact.append(curves.Line(
            (-length / 2.0, 0.0, 0.0),
            (-length / 2.0, 0.0, contact_radius - contact_curvature),
            line_resolution
        ))
        left_contact.append(curves.Bezier(
            (-length / 2.0, 0.0, contact_radius - contact_curvature),
            (0.0, 0.0, contact_curvature * weight),
            (-length / 2.0 + contact_curvature, 0.0, contact_radius),
            (-contact_curvature * weight, 0.0, 0.0),
            edge_resolution
        ))
        left_contact.append(curves.Line(
            (-length / 2.0 + contact_curvature, 0.0, contact_radius),
            (-length / 2.0 + contact_length - contact_curvature, 0.0, contact_radius),
            line_resolution
        ))
        left_contact.append(curves.Bezier(
            (-length / 2.0 + contact_length - contact_curvature, 0.0, contact_radius),
            (contact_curvature * weight, 0.0, 0.0),
            (-length / 2.0 + contact_length, 0.0, contact_radius - contact_curvature),
            (0.0, 0.0, contact_curvature * weight),
            edge_resolution
        ))
        left_contact.append(curves.Line(
            (-length / 2.0 + contact_length, 0.0, contact_radius - contact_curvature),
            (-length / 2.0 + contact_length, 0.0, body_radius - body_curvature),
            line_resolution
        ))

        right_contact = copy.deepcopy(left_contact)
        right_contact.reverse()
        for segment in right_contact:
            segment.apply(rotation)
            segment.reverse()

        return [left_contact, right_contact]

    def generate(self, materials, resolutions, _, descriptor):
        length = primitives.hmils(descriptor['body']['length'] + descriptor['pins']['length'] * 2.0)
        body_curvature = primitives.hmils(descriptor['body']['radius'] / 5.0)
        body_radius = primitives.hmils(descriptor['body']['radius'])
        contact_curvature = primitives.hmils(descriptor['pins']['length'] / 10.0)
        contact_length = primitives.hmils(descriptor['pins']['length'])
        contact_radius = primitives.hmils(descriptor['pins']['radius'])

        try:
            band_length = primitives.hmils(descriptor['band']['length'])
        except KeyError:
            band_length = 0.0

        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0

        axis = np.array([1.0, 0.0, 0.0])
        meshes = []

        # Polarity mark
        band_curves = MELF.build_band_curves(
            body_radius=body_radius,
            band_length=band_length,
            band_offset=band_offset,
            line_resolution=resolutions['line']
        )
        if len(band_curves) > 0:
            band_slices = []
            for entry in band_curves:
                band_slices.append(curves.rotate(curve=entry, axis=axis,
                                                 edges=resolutions['circle']))
            band_meshes = []
            for entry in band_slices:
                band_meshes.append(geometry.build_rotation_mesh(slices=entry, wrap=True,
                                                                invert=True))

            joined_mesh = model.Mesh()
            for mesh in band_meshes:
                joined_mesh.append(mesh)
            joined_mesh.optimize()
            if 'MELF.Band' in materials:
                joined_mesh.appearance().material = materials['MELF.Band']
            meshes.append(joined_mesh)

        # Glass body
        body_curves = MELF.build_body_curves(length=length,
            body_curvature=body_curvature,
            body_radius=body_radius,
            contact_length=contact_length,
            band_length=band_length,
            band_offset=band_offset,
            edge_resolution=resolutions['body'],
            line_resolution=resolutions['line']
        )
        body_slices = []
        for entry in body_curves:
            body_slices.append(curves.rotate(curve=entry, axis=axis, edges=resolutions['circle']))
        body_meshes = []
        for entry in body_slices:
            body_meshes.append(geometry.build_rotation_mesh(slices=entry, wrap=True,
                                                            invert=True))

        joined_mesh = model.Mesh()
        for mesh in body_meshes:
            joined_mesh.append(mesh)
        joined_mesh.optimize()
        if 'MELF.Glass' in materials:
            joined_mesh.appearance().material = materials['MELF.Glass']
        meshes.append(joined_mesh)

        # Contacts
        contact_curves = MELF.build_contact_curves(
            length=length,
            body_curvature=body_curvature,
            body_radius=body_radius,
            contact_curvature=contact_curvature,
            contact_length=contact_length,
            contact_radius=contact_radius,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )
        contact_slices = []
        for entry in contact_curves:
            contact_slices.append(curves.rotate(curve=entry, axis=axis,
                                                edges=resolutions['circle']))
        contact_meshes = []
        for entry in contact_slices:
            contact_meshes.append(geometry.build_rotation_mesh(slices=entry, wrap=True,
                                                               invert=True))

        joined_mesh = model.Mesh()
        for mesh in contact_meshes:
            joined_mesh.append(mesh)
        joined_mesh.optimize()
        if 'MELF.Lead' in materials:
            joined_mesh.appearance().material = materials['MELF.Lead']
        meshes.append(joined_mesh)

        for mesh in meshes:
            mesh.translate(np.array([0.0, 0.0, contact_radius]))
        return meshes


class SOT:
    BODY_CHAMFER = primitives.hmils(0.05)
    BODY_OFFSET_Z = primitives.hmils(0.1)

    BAND_WIDTH = primitives.hmils(0.1)

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
                    self.planar_offset = -abs(self.shape[1] * math.sin(slope) / 2.0)
                    self.vertical_offset = self.shape[1] * math.cos(slope) / 2.0
                    if slope < 0:
                        self.vertical_offset = -self.vertical_offset
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

    def generate_body(self, materials, resolutions, descriptor):
        body_chamfer = SOT.BODY_CHAMFER
        body_size = primitives.hmils(descriptor['body']['size'])

        # Special case for packages with two pins: match orientation for Chip footprints
        swap_xy = descriptor['pins']['count'] == 2
        if swap_xy:
            body_size[0], body_size[1] = body_size[1], body_size[0]

        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0

        try:
            flat_pin = descriptor['pins']['flat']
        except KeyError:
            flat_pin = False

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

        dot_offset = -(body_size[0:2] / 2.0 - SOT.MARK_MARGIN)
        body_offset_z = body_size[2] / 2.0
        if not flat_pin:
            body_offset_z += SOT.BODY_OFFSET_Z

        meshes = []

        body_mesh = primitives.make_box_with_mark(
            size=body_size,
            chamfer=body_chamfer,
            edge_resolution=resolutions['edge'],
            line_resolution=body_resolutions,
            band_size=SOT.BAND_WIDTH,
            band_offset=band_offset,
            mark_radius=dot_radius,
            mark_offset=dot_offset,
            mark_resolution=resolutions['circle']
        )

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

        if dot_radius is not None:
            dot_mesh = geometry.Circle(dot_radius, resolutions['circle'])
            dot_mesh.translate(np.array([*dot_offset, body_offset_z + body_size[2] / 2.0]))

            if f'{self.material}.Mark' in materials:
                dot_mesh.appearance().material = materials[f'{self.material}.Mark']
            dot_mesh.rename('Mark')
            meshes.append(dot_mesh)

        if swap_xy:
            for mesh in meshes:
                mesh.rotate((0.0, 0.0, 1.0), -math.pi / 2.0)
        return meshes

    def generate_pins(self, materials, resolutions, descriptor):
        try:
            flat_pin = descriptor['pins']['flat']
        except KeyError:
            flat_pin = False
        try:
            pin_pitch = primitives.hmils(descriptor['pins']['pitch'])
        except KeyError:
            pin_pitch = 0.0
        try:
            pin_slope = np.deg2rad(descriptor['pins']['slope'])
        except KeyError:
            pin_slope = np.deg2rad(10.0)

        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0
        try:
            band_inversion = descriptor['band']['inverse']
        except KeyError:
            band_inversion = flat_pin

        body_size = primitives.hmils(descriptor['body']['size'])
        if descriptor['pins']['count'] == 2:
            # Special case for packages with two pins: match orientation for Chip footprints
            body_size[0], body_size[1] = body_size[1], body_size[0]

        band_width_proj = SOT.BAND_WIDTH * math.sqrt(0.5)
        if band_inversion:
            body_slope = -math.atan(band_width_proj / (body_size[2] / 2.0 + band_offset))
        else:
            body_slope = math.atan(band_width_proj / (body_size[2] / 2.0 - band_offset))

        pin_height = body_size[2] / 2.0 + band_offset
        if not flat_pin:
            pin_height += SOT.BODY_OFFSET_Z

        try:
            pin_pattern = SOT.PinDesc.make_pattern(body_slope, descriptor['pins']['default'])
        except KeyError:
            pin_pattern = None

        pin_entries = {}
        for i in range(1, descriptor['pins']['count'] + 1):
            key = str(i)
            try:
                if descriptor['pins'][key] is not None:
                    pin_entries[i] = SOT.PinDesc(pin_pattern, body_slope, descriptor['pins'][key])
            except KeyError:
                pin_entries[i] = SOT.PinDesc(pin_pattern)
        pin_groups = set(pin_entries.values())
        pin_group_meshes = {}

        for group in pin_groups:
            if flat_pin:
                mesh = primitives.make_flat_pin_mesh(
                    pin_shape_size=group.shape,
                    pin_length=group.length,
                    end_slope=body_slope,
                    edge_resolution=resolutions['chamfer'],
                    line_resolution=resolutions['line']
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
            size=body_size[0:2] + band_width_proj * 2.0,
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
        meshes = []
        meshes.extend(self.generate_body(materials, resolutions, descriptor))
        meshes.extend(self.generate_pins(materials, resolutions, descriptor))
        return meshes


class SOD(SOT):
    def __init__(self):
        super().__init__('SOD')


types = [
    Chip,
    MELF,
    SOD,
    SOT
]
