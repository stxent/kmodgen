#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# switches.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class Button(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=Button.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.pitch = numpy.array(descriptor['pins']['pitch'])
        self.shielding = descriptor['pins']['shielding']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        pads.append(exporter.SmdPad(1, self.pad_size, self.pitch / 2.0 * [-1, +1]))
        pads.append(exporter.SmdPad(2, self.pad_size, self.pitch / 2.0 * [+1, +1]))
        pads.append(exporter.SmdPad(3, self.pad_size, self.pitch / 2.0 * [+1, -1]))
        pads.append(exporter.SmdPad(4, self.pad_size, self.pitch / 2.0 * [-1, -1]))

        if self.shielding:
            pads.append(exporter.SmdPad(5, self.pad_size, self.pitch / 2.0 * [1, 0]))

        # Body outline
        bounding_box = numpy.array([
            0.0,
            self.pitch[1] + self.pad_size[1] + self.gap * 2.0 + self.thickness])
        outline_size = numpy.maximum(self.body_size, bounding_box)
        outline = exporter.Rect(outline_size / 2.0, -outline_size / 2.0, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        # Central circle
        silkscreen.append(exporter.Circle((0.0, 0.0), min(self.body_size) / 4.0, self.thickness))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


class DIP(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=DIP.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.count = descriptor['pins']['count']
        self.pitch = numpy.array(descriptor['pins']['pitch'])

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Body outline
        top_corner = self.body_size / 2.0
        objects.append(exporter.Rect(top_corner, -top_corner, self.thickness))

        # Horizontal offset to the first pin
        columns = int(self.count / 2)
        first_pin_offset = float(columns - 1) / 2.0 * self.pitch[0]

        pads = []
        for i in range(0, columns):
            x_offset = i * self.pitch[0] - first_pin_offset
            y_offset = self.pitch[1] / 2.0
            pads.append(exporter.SmdPad(i + 1, self.pad_size, (x_offset, y_offset)))
            pads.append(exporter.SmdPad(self.count - i, self.pad_size, (x_offset, -y_offset)))

        objects.extend(pads)
        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None


types = [Button, DIP]
