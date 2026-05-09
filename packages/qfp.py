#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy as np

import primitives
from wrlconv import geometry
from wrlconv import model


class QFP:
    BAND_OFFSET = primitives.hmils(0.0)
    BAND_WIDTH = primitives.hmils(0.1)

    BODY_CHAMFER = primitives.hmils(0.1)
    BODY_OFFSET_Z = primitives.hmils(0.1)
    BODY_ROUNDNESS = primitives.hmils(0.5)

    MARK_RADIUS = primitives.hmils(0.5)
    PIN_SLOPE = 10.0

    @staticmethod
    def generate_package_pins(pattern, count, size, offset, pitch):
        def make_pin(x, y, angle, number): # pylint: disable=invalid-name
            pin = model.Mesh(parent=pattern, name='Pin{:d}'.format(number))
            pin.translate([x, y, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        pins = []

        # Horizontal pins
        y_offset = size[1] / 2.0 + offset
        for i in range(count[0]):
            x_offset = pitch * (i - (count[0] - 1) / 2.0)
            pins.append(make_pin(x_offset, y_offset, math.pi,
                i + 1))
            pins.append(make_pin(-x_offset, -y_offset, 0.0,
                i + 1 + count[0] + count[1]))

        # Vertical pins
        x_offset = size[0] / 2.0 + offset
        for i in range(count[1]):
            y_offset = pitch * (i - (count[1] - 1) / 2.0)
            pins.append(make_pin(x_offset, -y_offset, math.pi / 2.0,
                i + 1 + count[0]))
            pins.append(make_pin(-x_offset, y_offset, -math.pi / 2.0,
                i + 1 + count[0] * 2 + count[1]))

        return pins

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(descriptor['body']['size'])
        pin_count = [descriptor['pins']['columns'], descriptor['pins']['rows']]
        pin_height = body_size[2] / 2.0 + QFP.BODY_OFFSET_Z
        pin_pitch = primitives.hmils(descriptor['pins']['pitch'])
        pin_shape = primitives.hmils(descriptor['pins']['shape'])
        dot_offset = QFP.calc_mark_offset(pin_count, pin_pitch)

        body_slope = math.atan(2.0 * QFP.BAND_WIDTH / body_size[2])
        pin_offset = pin_shape[1] * math.sin(body_slope) / 2.0

        body_mesh, dot_mesh = primitives.make_rounded_box(
            size=body_size,
            roundness=QFP.BODY_ROUNDNESS,
            chamfer=QFP.BODY_CHAMFER,
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line'],
            plane_resolution=max(resolutions['line'], 2),
            band_size=QFP.BAND_WIDTH,
            band_offset=QFP.BAND_OFFSET,
            mark_radius=QFP.MARK_RADIUS,
            mark_offset=dot_offset,
            mark_resolution=resolutions['circle']
        )

        if 'QFP.Plastic' in materials:
            body_mesh.appearance().material = materials['QFP.Plastic']
        body_mesh.translate(np.array([0.0, 0.0, body_size[2] / 2.0 + QFP.BODY_OFFSET_Z]))
        body_mesh.rename('Body')

        if 'QFP.Dot' in materials:
            dot_mesh.appearance().material = materials['QFP.Dot']
        dot_mesh.translate(np.array([0.0, 0.0, body_size[2] / 2.0 + QFP.BODY_OFFSET_Z]))
        dot_mesh.rename('Dot')

        pin_mesh = primitives.make_pin_mesh(
            pin_shape_size=pin_shape,
            pin_height=pin_height + pin_shape[1] * math.cos(body_slope) / 2.0,
            pin_length=primitives.hmils(descriptor['pins']['length']) + pin_offset,
            pin_slope=np.deg2rad(QFP.PIN_SLOPE),
            end_slope=body_slope,
            edge_resolution=resolutions['chamfer'],
            line_resolution=resolutions['line'],
            slope_resolution=resolutions['edge']
        )
        if 'QFP.Lead' in materials:
            pin_mesh.appearance().material = materials['QFP.Lead']

        pins = QFP.generate_package_pins(
            pattern=pin_mesh,
            count=pin_count,
            size=body_size,
            offset=QFP.BAND_WIDTH - pin_offset,
            pitch=pin_pitch
        )

        return pins + [body_mesh] + [dot_mesh]

    @staticmethod
    def calc_mark_offset(count, pitch):
        first_pin_offset = (np.asarray(count, dtype=np.float32) - 1.0) * pitch / 2.0
        mark_offset = -first_pin_offset + pitch
        return np.array([*mark_offset, 0.0])


types = [QFP]
