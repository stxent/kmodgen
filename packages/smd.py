#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import numpy

from wrlconv import curves
from wrlconv import geometry
from wrlconv import model
import primitives
from packages import generic


class Chip(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(Chip.PIVOT_BOUNDING_BOX_CENTER)


class MELF:
    EDGE_COUNT = 24

    BODY_RESOLUTION    = 3
    CONTACT_RESOLUTION = 2
    LINE_RESOLUTION    = 1

    def __init__(self):
        pass

    @staticmethod
    def build_band_curves(body_radius, band_length, band_offset, line_resolution):
        band = []

        if band_length > 0.0:
            band.append(curves.Line(
                (band_offset - band_length / 2.0, 0.0, body_radius),
                (band_offset + band_length / 2.0, 0.0, body_radius), line_resolution))

        return [band]

    @staticmethod
    def build_body_curves(length, body_curvature, body_radius, contact_length, band_length,
                          band_offset, edge_resolution, line_resolution):
        weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
        left_part, right_part = [], []

        # Left rounded edge
        left_part.append(curves.Bezier(
            (-length / 2.0 + contact_length, 0.0, body_radius - body_curvature),
            (0.0, 0.0, body_curvature * weight),
            (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
            (-body_curvature * weight, 0.0, 0.0),
            edge_resolution))

        if band_length > 0.0:
            # Package glass to the left of the band
            left_part.append(curves.Line(
                (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
                (band_offset - band_length / 2.0, 0.0, body_radius), line_resolution))
            # Package glass to the right of the band
            right_part.append(curves.Line(
                (band_offset + band_length / 2.0, 0.0, body_radius),
                (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
                line_resolution))
        else:
            left_part.append(curves.Line(
                (-length / 2.0 + contact_length + body_curvature, 0.0, body_radius),
                (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
                line_resolution))

        # Right rounded edge
        right_part.append(curves.Bezier(
            (length / 2.0 - contact_length - body_curvature, 0.0, body_radius),
            (body_curvature * weight, 0.0, 0.0),
            (length / 2.0 - contact_length, 0.0, body_radius - body_curvature),
            (0.0, 0.0, body_curvature * weight),
            edge_resolution))

        return [left_part, right_part]

    @staticmethod
    def build_contact_curves(length, body_curvature, body_radius, contact_curvature,
                             contact_length, contact_radius, edge_resolution, line_resolution):
        rotation = model.Transform(matrix=model.make_rotation_matrix(numpy.array([0.0, 0.0, 1.0]),
            math.pi))
        weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
        left_contact = []

        # Left contact
        left_contact.append(curves.Line(
            (-length / 2.0, 0.0, 0.0),
            (-length / 2.0, 0.0, contact_radius - contact_curvature),
            line_resolution))
        left_contact.append(curves.Bezier(
            (-length / 2.0, 0.0, contact_radius - contact_curvature),
            (0.0, 0.0, contact_curvature * weight),
            (-length / 2.0 + contact_curvature, 0.0, contact_radius),
            (-contact_curvature * weight, 0.0, 0.0),
            edge_resolution))
        left_contact.append(curves.Line(
            (-length / 2.0 + contact_curvature, 0.0, contact_radius),
            (-length / 2.0 + contact_length - contact_curvature, 0.0, contact_radius),
            line_resolution))
        left_contact.append(curves.Bezier(
            (-length / 2.0 + contact_length - contact_curvature, 0.0, contact_radius),
            (contact_curvature * weight, 0.0, 0.0),
            (-length / 2.0 + contact_length, 0.0, contact_radius - contact_curvature),
            (0.0, 0.0, contact_curvature * weight),
            edge_resolution))
        left_contact.append(curves.Line(
            (-length / 2.0 + contact_length, 0.0, contact_radius - contact_curvature),
            (-length / 2.0 + contact_length, 0.0, body_radius - body_curvature),
            line_resolution))

        right_contact = copy.deepcopy(left_contact)
        right_contact.reverse()
        for segment in right_contact:
            segment.apply(rotation)
            segment.reverse()

        return [left_contact, right_contact]

    def generate(self, materials, _, descriptor):
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

        axis = numpy.array([1.0, 0.0, 0.0])
        meshes = []

        # Polarity mark
        band_curves = MELF.build_band_curves(
            body_radius=body_radius,
            band_length=band_length,
            band_offset=band_offset,
            line_resolution=MELF.LINE_RESOLUTION)
        if len(band_curves) > 0:
            band_slices = []
            for entry in band_curves:
                band_slices.append(curves.rotate(curve=entry, axis=axis, edges=MELF.EDGE_COUNT))
            band_meshes = []
            for entry in band_slices:
                band_meshes.append(curves.create_rotation_mesh(slices=entry, wrap=True,
                                                               inverse=True))

            joined_mesh = model.Mesh()
            for mesh in band_meshes:
                joined_mesh.append(mesh)
            joined_mesh.optimize()
            if 'Band' in materials:
                joined_mesh.appearance().material = materials['Band']
            meshes.append(joined_mesh)

        # Glass body
        body_curves = MELF.build_body_curves(length=length,
            body_curvature=body_curvature,
            body_radius=body_radius,
            contact_length=contact_length,
            band_length=band_length,
            band_offset=band_offset,
            edge_resolution=MELF.BODY_RESOLUTION,
            line_resolution=MELF.LINE_RESOLUTION)
        body_slices = []
        for entry in body_curves:
            body_slices.append(curves.rotate(curve=entry, axis=axis, edges=MELF.EDGE_COUNT))
        body_meshes = []
        for entry in body_slices:
            body_meshes.append(curves.create_rotation_mesh(slices=entry, wrap=True,
                                                           inverse=True))

        joined_mesh = model.Mesh()
        for mesh in body_meshes:
            joined_mesh.append(mesh)
        joined_mesh.optimize()
        if 'Glass' in materials:
            joined_mesh.appearance().material = materials['Glass']
        meshes.append(joined_mesh)

        # Contacts
        contact_curves = MELF.build_contact_curves(
            length=length,
            body_curvature=body_curvature,
            body_radius=body_radius,
            contact_curvature=contact_curvature,
            contact_length=contact_length,
            contact_radius=contact_radius,
            edge_resolution=MELF.CONTACT_RESOLUTION,
            line_resolution=MELF.LINE_RESOLUTION)
        contact_slices = []
        for entry in contact_curves:
            contact_slices.append(curves.rotate(curve=entry, axis=axis, edges=MELF.EDGE_COUNT))
        contact_meshes = []
        for entry in contact_slices:
            contact_meshes.append(curves.create_rotation_mesh(slices=entry, wrap=True,
                                                              inverse=True))

        joined_mesh = model.Mesh()
        for mesh in contact_meshes:
            joined_mesh.append(mesh)
        joined_mesh.optimize()
        if 'Contact' in materials:
            joined_mesh.appearance().material = materials['Contact']
        meshes.append(joined_mesh)

        for mesh in meshes:
            mesh.translate(numpy.array([0.0, 0.0, contact_radius]))
        return meshes


class SOT:
    BODY_CHAMFER = primitives.hmils(0.05)
    BODY_OFFSET_Z = primitives.hmils(0.1)

    BAND_WIDTH = primitives.hmils(0.1)

    MARK_MARGIN = primitives.hmils(0.4)
    MARK_RADIUS = primitives.hmils(0.2)

    CHAMFER_RESOLUTION = 1
    EDGE_RESOLUTION    = 3
    LINE_RESOLUTION    = 1


    class PinDesc:
        def __init__(self, pattern, slope=None, descriptor=None):
            if pattern is None and descriptor is None:
                # Not enough information
                raise Exception()

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
                raise Exception()

            return cls(None, slope, descriptor)


    def __init__(self):
        pass

    @staticmethod
    def generate_body(materials, descriptor):
        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0

        try:
            flat_pin = descriptor['pins']['flat']
        except KeyError:
            flat_pin = False

        try:
            mark_radius = SOT.MARK_RADIUS if primitives.hmils(descriptor['mark']['dot']) else None
        except KeyError:
            mark_radius = None

        body_size = primitives.hmils(descriptor['body']['size'])
        mark_offset = -(body_size[0:2] / 2.0 - SOT.MARK_MARGIN)

        body_offset_z = body_size[2] / 2.0
        if not flat_pin:
            body_offset_z += SOT.BODY_OFFSET_Z

        body_mesh = primitives.make_box(
            size=body_size,
            chamfer=SOT.BODY_CHAMFER,
            edge_resolution=SOT.EDGE_RESOLUTION,
            line_resolution=SOT.LINE_RESOLUTION,
            band_size=SOT.BAND_WIDTH,
            band_offset=band_offset,
            mark_radius=mark_radius,
            mark_offset=mark_offset,
            mark_resolution=SOT.EDGE_RESOLUTION * 8
        )
        if mark_radius is not None:
            mark_mesh = geometry.Circle(mark_radius, SOT.EDGE_RESOLUTION * 8)
            mark_mesh.translate(numpy.array([*mark_offset, body_offset_z + body_size[2] / 2.0]))
        else:
            mark_mesh = None

        meshes = []

        if 'Body' in materials:
            body_mesh.appearance().material = materials['Body']
        body_mesh.translate(numpy.array([0.0, 0.0, body_offset_z]))
        body_mesh.rename('Body')
        meshes.append(body_mesh)

        if mark_mesh is not None:
            if 'Mark' in materials:
                mark_mesh.appearance().material = materials['Mark']
            mark_mesh.rename('Mark')
            meshes.append(mark_mesh)

        return meshes

    @staticmethod
    def generate_pins(materials, descriptor):
        try:
            flat_pin = descriptor['pins']['flat']
        except KeyError:
            flat_pin = False
        try:
            pin_slope = descriptor['pins']['slope'] * math.pi / 180.0
        except KeyError:
            pin_slope = math.pi * (10.0 / 180.0)

        try:
            band_offset = primitives.hmils(descriptor['band']['offset'])
        except KeyError:
            band_offset = 0.0
        try:
            band_inversion = descriptor['band']['inverse']
        except KeyError:
            band_inversion = flat_pin

        body_size = primitives.hmils(descriptor['body']['size'])
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
            mesh = primitives.make_pin_mesh(
                pin_shape_size=group.shape,
                pin_height=pin_height + group.vertical_offset,
                pin_length=group.length,
                pin_slope=pin_slope,
                end_slope=body_slope,
                chamfer_resolution=SOT.CHAMFER_RESOLUTION,
                edge_resolution=SOT.EDGE_RESOLUTION,
                line_resolution=SOT.LINE_RESOLUTION,
                flat=flat_pin
            )

            if 'Pin' in materials:
                mesh.appearance().material = materials['Pin']

            pin_group_meshes[hash(group)] = mesh

        return SOT.generate_pin_rows(
            count=descriptor['pins']['count'],
            size=body_size[0:2] + band_width_proj * 2.0,
            pitch=primitives.hmils(descriptor['pins']['pitch']),
            patterns=pin_group_meshes,
            entries=pin_entries)

    @staticmethod
    def generate_pin_rows(count, size, pitch, patterns, entries):
        def make_pin(mesh, position, angle, number):
            pin = model.Mesh(parent=mesh, name='Pin{:d}'.format(number))
            pin.translate([*position, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        columns = int(count / 2)
        first_pin_offset = pitch * (columns - 1) / 2.0
        y_offset = size[1] / 2.0

        meshes = []
        for i in range(1, columns + 1):
            x_offset = pitch * (i - 1) - first_pin_offset

            if i + columns in entries:
                entry = entries[i + columns]
                mesh = patterns[hash(entry)]
                meshes.append(make_pin(mesh, [x_offset, y_offset + entry.planar_offset],
                    math.pi, i + columns))

            if i in entries:
                entry = entries[i]
                mesh = patterns[hash(entry)]
                meshes.append(make_pin(mesh, [-x_offset, -(y_offset + entry.planar_offset)],
                    0.0, i))

        return meshes

    def generate(self, materials, _, descriptor):
        return SOT.generate_body(materials, descriptor) + SOT.generate_pins(materials, descriptor)


types = [
    Chip,
    MELF,
    SOT
]
