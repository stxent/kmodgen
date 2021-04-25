#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# sop.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter
import primitives


class SOP(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=SOP.describe(descriptor), spec=spec)

        try:
            self.pad_size = numpy.array(descriptor['pads']['regularPadSize'])
        except KeyError:
            self.pad_size = numpy.array(descriptor['pads']['size'])

        try:
            self.side_pad_size = numpy.array(descriptor['pads']['sidePadSize'])
        except KeyError:
            self.side_pad_size = self.pad_size

        self.body_size = numpy.array(descriptor['body']['size'])
        self.rows = int(descriptor['pins']['count'] / 2)
        self.margin = descriptor['pads']['margin']
        self.pitch = descriptor['pins']['pitch']
        self.side_pitch = self.pitch + (self.side_pad_size[0] - self.pad_size[0]) / 2.0
        self.title = '{:s}-{:d}'.format(descriptor['package']['subtype'],
            descriptor['pins']['count'])

    def pad(self, position, count):
        return self.side_pad_size if position in (0, count - 1) else self.pad_size

    def spacing(self, position, count):
        res = 0.0
        if position > 0:
            res += self.pitch * (position - 1)
        if position >= 1:
            res += self.side_pitch
        if position == count - 1:
            res += self.side_pitch - self.pitch
        return res

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.title, (0.0, 0.0), self.thickness, self.font))

        # Horizontal offset to the first pin
        first_pin_offset = float(self.rows - 3) * self.pitch / 2.0 + self.side_pitch

        # Body outline
        outline_margin = numpy.array([0.0, (self.margin - self.gap) * 2.0 - self.thickness, 0.0])
        outline_size = numpy.minimum(self.body_size, self.body_size + outline_margin)
        top_corner = outline_size / 2.0
        silkscreen.append(exporter.Rect(top_corner, -top_corner, self.thickness))

        # Outer first pin mark
        dot_mark_position = numpy.array([
            -(first_pin_offset + self.side_pad_size[0] / 2.0 + self.gap + self.thickness),
            (self.body_size[1] + self.pad_size[1]) / 2.0 + self.margin])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Inner first pin mark
        tri_mark_offset = 1.0
        tri_mark_points = [
            (-top_corner[0], top_corner[1] - tri_mark_offset),
            (-top_corner[0], top_corner[1]),
            (-top_corner[0] + tri_mark_offset, top_corner[1])]
        silkscreen.append(exporter.Poly(tri_mark_points, self.thickness, exporter.Layer.SILK_FRONT))

        # Horizontal pads
        y_offset = (self.body_size[1] + self.pad_size[1]) / 2.0 + self.margin
        for i in range(0, self.rows):
            x_offset = self.spacing(i, self.rows) - first_pin_offset
            pads.append(exporter.SmdPad(i + 1, self.pad(i, self.rows), (x_offset, y_offset)))
            pads.append(exporter.SmdPad(i + 1 + self.rows, self.pad(i, self.rows),
                (-x_offset, -y_offset)))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor:
            return descriptor['description']

        width_str = primitives.round1f(descriptor['body']['size'][0])
        pitch_str = primitives.round2f(descriptor['pins']['pitch'])
        return '{:d} leads, body width {:s} mm, pitch {:s} mm'.format(
            descriptor['pins']['count'], width_str, pitch_str)


types = [SOP]
