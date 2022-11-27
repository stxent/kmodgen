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

        heatsink_size = None
        try:
            heatsink_size = numpy.array(descriptor['pads']['heatsink'])
        except KeyError:
            pass
        if heatsink_size is None:
            try:
                heatsink_size = numpy.array(descriptor['heatsink']['size'])
            except KeyError:
                pass
        self.heatsink_size = heatsink_size

        try:
            columns, rows = descriptor['pins']['columns'], descriptor['pins']['rows']
        except KeyError:
            columns, rows = descriptor['pins']['count'] // 2, 0
        self.count = numpy.array([columns, rows])

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.margin = descriptor['pins']['margin']
        self.pitch = descriptor['pins']['pitch']

        prefix = 'QFN' if rows > 0 else 'DFN'
        self.title = f'{prefix}-{sum(self.count) * 2}'

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
        top_corner_from_body = self.body_size[0:2] / 2.0
        top_corner_from_pins = numpy.array([
            first_pin_offset[0] + (self.pad_size[0] + self.thickness) / 2.0 + self.gap,
            first_pin_offset[1] + (self.pad_size[0] + self.thickness) / 2.0 + self.gap])
        top_corner = numpy.maximum(top_corner_from_body, top_corner_from_pins)
        silkscreen_raw.extend(exporter.Rect(top_corner, -top_corner, self.thickness).lines)

        # Outer first pin mark
        dot_offset_from_pin = top_corner_from_pins[0] + self.thickness / 2.0
        dot_offset_from_body = (self.body_size[0] - self.thickness) / 2.0
        dot_mark_x_offset = -max(dot_offset_from_pin, dot_offset_from_body)
        dot_mark_y_offset = top_corner[1] + self.gap + self.thickness * 1.5
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

        try:
            columns, rows = descriptor['pins']['columns'], descriptor['pins']['rows']
        except KeyError:
            columns, rows = descriptor['pins']['count'] // 2, 0

        pin_count = (columns + rows) * 2
        size_str = [primitives.round1f(x) for x in descriptor['body']['size'][0:2]]
        height_str = primitives.round2f(descriptor['body']['size'][2])
        pitch_str = primitives.round2f(descriptor['pins']['pitch'])
        return '{:d} leads, body {:s}x{:s}x{:s} mm, pitch {:s} mm'.format(
            pin_count, size_str[0], size_str[1], height_str, pitch_str)


class DFN(QFN):
    pass


class LGA(QFN):
    def __init__(self, spec, descriptor):
        super().__init__(spec=spec, descriptor=descriptor)
        self.title = f'LGA-{sum(self.count) * 2}'


types = [QFN, DFN, LGA]
