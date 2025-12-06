#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# qfp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy as np

import exporter
import primitives


class QFP(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=QFP.describe(descriptor), spec=spec)

        try:
            self.pad_size = np.array(descriptor['pads']['regularPadSize'])
        except KeyError:
            self.pad_size = np.array(descriptor['pads']['size'])

        try:
            self.side_pad_size = np.array(descriptor['pads']['sidePadSize'])
        except KeyError:
            self.side_pad_size = self.pad_size

        self.body_size = np.array(descriptor['body']['size'])
        self.count = np.array([descriptor['pins']['columns'], descriptor['pins']['rows']])
        self.margin = descriptor['pads']['margin']
        self.pitch = descriptor['pins']['pitch']
        self.side_pitch = self.pitch + (self.side_pad_size[0] - self.pad_size[0]) / 2.0
        self.title = 'QFP-{:d}'.format(sum(self.count) * 2)

    def pad(self, position, count, rev):
        x_offset, y_offset = self.side_pad_size if position in (0, count - 1) else self.pad_size
        return np.array([x_offset, y_offset]) if not rev else np.array([y_offset, x_offset])

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

        # Horizontal and vertical offsets to first pins on each side
        first_pin_offset = np.asarray(self.count, dtype=np.float32) - 3.0
        first_pin_offset = first_pin_offset * self.pitch / 2.0 + self.side_pitch

        # Body outline
        outline_margin = (self.margin - self.gap) * 2.0 - self.thickness
        outline_size = np.minimum(self.body_size, self.body_size + outline_margin)
        top_corner = outline_size / 2.0
        silkscreen.append(exporter.Rect(top_corner, -top_corner, self.thickness))

        # Outer first pin mark
        dot_mark_position = np.array([
            -(first_pin_offset[0] + self.side_pad_size[0] / 2.0 + self.gap + self.thickness),
            (self.body_size[1] + self.pad_size[1]) / 2.0 + self.margin
        ])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0,
                                          self.thickness, True))

        # Inner first pin mark
        tri_mark_offset = 1.0
        tri_mark_points = [
            np.array([-top_corner[0], top_corner[1] - tri_mark_offset]),
            np.array([-top_corner[0], top_corner[1]]),
            np.array([-top_corner[0] + tri_mark_offset, top_corner[1]])
        ]
        silkscreen.append(exporter.Poly(tri_mark_points, self.thickness, True,
                                        exporter.Layer.SILK_FRONT))

        # Horizontal pads
        y_offset = (self.body_size[1] + self.pad_size[1]) / 2.0 + self.margin
        pad = lambda x: self.pad(x, self.count[0], False)
        for i in range(0, self.count[0]):
            x_offset = self.spacing(i, self.count[0]) - first_pin_offset[0]
            pads.append(exporter.SmdPad(str(1 + i), pad(i),
                                        np.array([x_offset, y_offset])))
            pads.append(exporter.SmdPad(str(1 + i + self.count[0] + self.count[1]), pad(i),
                                        np.array([-x_offset, -y_offset])))

        # Vertical pads
        x_offset = (self.body_size[0] + self.pad_size[1]) / 2.0 + self.margin
        pad = lambda x: self.pad(x, self.count[1], True)
        for j in range(0, self.count[1]):
            y_offset = self.spacing(j, self.count[1]) - first_pin_offset[1]
            pads.append(exporter.SmdPad(str(1 + j + self.count[0]), pad(j),
                                        np.array([x_offset, -y_offset])))
            pads.append(exporter.SmdPad(str(1 + j + 2 * self.count[0] + self.count[1]), pad(j),
                                        np.array([-x_offset, y_offset])))

        pads.sort(key=lambda x: int(x.text))
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor:
            return descriptor['description']

        pin_count = (descriptor['pins']['columns'] + descriptor['pins']['rows']) * 2
        size_str = [primitives.round1f(x) for x in descriptor['body']['size'][0:2]]
        height_str = primitives.round2f(descriptor['body']['size'][2])
        pitch_str = primitives.round2f(descriptor['pins']['pitch'])
        return '{:d} leads, body {:s}x{:s}x{:s} mm, pitch {:s} mm'.format(
            pin_count, size_str[0], size_str[1], height_str, pitch_str)


types = [QFP]
