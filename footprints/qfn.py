#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# qfn.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter
import primitives


class QFN(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=QFN.describe(descriptor), spec=spec)

        try:
            self.heatsink_size = numpy.array(descriptor['heatsink']['size'])
        except KeyError:
            self.heatsink_size = None

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.count = numpy.array([descriptor['pins']['columns'], descriptor['pins']['rows']])
        self.margin = descriptor['pins']['margin']
        self.pitch = descriptor['pins']['pitch']
        self.title = 'QFN-{:d}'.format(sum(self.count) * 2)

    def pad(self, rev):
        x_offset, y_offset = self.pad_size
        return numpy.array([x_offset, y_offset]) if not rev else numpy.array([y_offset, x_offset])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen_raw = []
        silkscreen.append(exporter.Label(self.title, (0.0, 0.0), self.thickness, self.font))

        # Horizontal and vertical offsets to first pins on each side
        first_pin_offset = (numpy.asfarray(self.count) - 1.0) * self.pitch / 2.0

        # Body outline
        top_corner = self.body_size / 2.0
        silkscreen_raw.extend(
            exporter.Rect(self.body_size / 2.0, -self.body_size / 2.0, self.thickness).lines)

        # Outer first pin mark
        dot_offset_from_pin = -(self.gap + (self.pad_size[0] + self.thickness) / 2.0
                                + first_pin_offset[0])
        dot_offset_from_body = -top_corner[0]
        dot_mark_x_offset = (dot_offset_from_pin + dot_offset_from_body) / 2.0
        dot_mark_y_offset = top_corner[1] + self.gap + self.thickness
        dot_mark_position = numpy.array([dot_mark_x_offset, dot_mark_y_offset])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Horizontal pads
        y_offset = self.body_size[1] / 2.0 + self.margin
        pad = lambda x: self.pad(False)
        for i in range(0, self.count[0]):
            x_offset = i * self.pitch - first_pin_offset[0]
            pads.append(exporter.SmdPad(1 + i, pad(i), (x_offset, y_offset)))
            pads.append(exporter.SmdPad(1 + i + self.count[0] + self.count[1], pad(i),
                (-x_offset, -y_offset)))

        # Vertical pads
        x_offset = self.body_size[0] / 2.0 + self.margin
        pad = lambda x: self.pad(True)
        for j in range(0, self.count[1]):
            y_offset = j * self.pitch - first_pin_offset[1]
            pads.append(exporter.SmdPad(1 + j + self.count[0], pad(j), (x_offset, -y_offset)))
            pads.append(exporter.SmdPad(1 + j + 2 * self.count[0] + self.count[1], pad(j),
                (-x_offset, y_offset)))

        # Central pad
        if self.heatsink_size is not None:
            pads.append(exporter.SmdPad(sum(self.count) * 2 + 1, self.heatsink_size, (0.0, 0.0)))

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in silkscreen_raw:
            silkscreen.extend(process_func(line))

        pads.sort(key=lambda x: x.number)
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


types = [QFN]
