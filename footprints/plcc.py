#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# plcc.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter
import primitives


class PLCC(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=PLCC.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.pitch = numpy.array(descriptor['pins']['pitch'])
        self.mapping = descriptor['pins']['names']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        axis_offsets = self.pitch / 2.0

        if len(self.mapping) == 2:
            pads.append(exporter.SmdPad(self.mapping[0], self.pad_size, (-axis_offsets[0], 0.0)))
            pads.append(exporter.SmdPad(self.mapping[1], self.pad_size, (axis_offsets[0], 0.0)))
        elif len(self.mapping) == 4:
            pads.append(exporter.SmdPad(self.mapping[0], self.pad_size,
                (-axis_offsets[0], axis_offsets[1])))
            pads.append(exporter.SmdPad(self.mapping[1], self.pad_size,
                (axis_offsets[0], axis_offsets[1])))
            pads.append(exporter.SmdPad(self.mapping[2], self.pad_size,
                (axis_offsets[0], -axis_offsets[1])))
            pads.append(exporter.SmdPad(self.mapping[3], self.pad_size,
                (-axis_offsets[0], -axis_offsets[1])))
        else:
            # Unsupported pin configuration
            raise Exception()

        # First pin mark
        dot_mark_position = numpy.array([
            -(axis_offsets[0] + self.pad_size[0] / 2.0 + self.gap + self.thickness),
            axis_offsets[1]])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Body outline
        outline = exporter.Rect(self.body_size / 2.0, -self.body_size / 2.0, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor:
            return descriptor['description']

        body_size = [primitives.round1f(x) for x in descriptor['body']['size'][0:2]]
        return 'Plastic Leaded Chip Carrier {:s}x{:s} mm'.format(*body_size)


types = [PLCC]
