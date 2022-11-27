#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math

from wrlconv import model
import primitives


class SOP:
    BODY_CHAMFER = primitives.hmils(0.1)
    BODY_OFFSET_Z = primitives.hmils(0.1)

    BAND_OFFSET = primitives.hmils(0.0)
    BAND_WIDTH = primitives.hmils(0.1)

    CHAMFER_RESOLUTION = 1
    EDGE_RESOLUTION    = 3
    LINE_RESOLUTION    = 1

    @staticmethod
    def generate_package_pins(pattern, count, size, offset, pitch):
        def make_pin(x, y, angle, number): # pylint: disable=invalid-name
            pin = model.Mesh(parent=pattern, name='Pin{:d}'.format(number))
            pin.translate([x, y, 0.0])
            pin.rotate([0.0, 0.0, 1.0], angle - math.pi / 2.0)
            return pin

        rows = int(count / 2)
        pins = []

        # Pins
        y_offset = size[1] / 2.0 + offset
        for i in range(0, rows):
            x_offset = pitch * (i - (rows - 1) / 2.0)
            pins.append(make_pin(x_offset, y_offset, math.pi, i + 1 + rows))
            pins.append(make_pin(-x_offset, -y_offset, 0.0, i + 1))

        return pins

    def generate(self, materials, _, descriptor):
        body_size = primitives.hmils(descriptor['body']['size'])
        pin_height = body_size[2] / 2.0 + SOP.BODY_OFFSET_Z
        pin_shape = primitives.hmils(descriptor['pins']['shape'])

        band_width_proj = SOP.BAND_WIDTH * math.sqrt(0.5)
        body_slope = math.atan(2.0 * band_width_proj / body_size[2])
        pin_offset = pin_shape[1] * math.sin(body_slope) / 2.0

        body_transform = model.Transform()
        body_transform.rotate([0.0, 0.0, 1.0], math.pi)
        body_transform.translate([0.0, 0.0, pin_height])

        body_mesh = primitives.make_sloped_box(
            size=body_size,
            chamfer=SOP.BODY_CHAMFER,
            slope=math.pi / 4.0,
            slope_height=body_size[2] / 5.0,
            edge_resolution=SOP.EDGE_RESOLUTION,
            line_resolution=SOP.LINE_RESOLUTION,
            band_size=SOP.BAND_WIDTH,
            band_offset=SOP.BAND_OFFSET
        )

        if 'Body' in materials:
            body_mesh.appearance().material = materials['Body']
        body_mesh.apply(body_transform)
        body_mesh.rename('Body')

        pin_mesh = primitives.make_pin_mesh(
            pin_shape_size=pin_shape,
            pin_height=pin_height + pin_shape[1] * math.cos(body_slope) / 2.0,
            pin_length=primitives.hmils(descriptor['pins']['length']) + pin_offset,
            pin_slope=math.pi * (10.0 / 180.0),
            end_slope=body_slope,
            chamfer_resolution=SOP.CHAMFER_RESOLUTION,
            edge_resolution=SOP.EDGE_RESOLUTION,
            line_resolution=SOP.LINE_RESOLUTION
        )
        if 'Pin' in materials:
            pin_mesh.appearance().material = materials['Pin']

        pins = SOP.generate_package_pins(
            pattern=pin_mesh,
            count=descriptor['pins']['count'],
            size=body_size,
            offset=band_width_proj - pin_offset,
            pitch=primitives.hmils(descriptor['pins']['pitch'])
        )

        return pins + [body_mesh]


types = [SOP]
