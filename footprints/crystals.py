#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# crystals.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy as np

import exporter
import primitives


class CrystalSMD(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=CrystalSMD.describe(descriptor), spec=spec)

        self.body_size = np.array(descriptor['body']['size'])
        self.pad_size = np.array(descriptor['pads']['size'])
        self.pitch = np.array(descriptor['pins']['pitch'])
        self.mapping = descriptor['pins']['names']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        axis_offsets = self.pitch / 2.0

        if len(self.mapping) == 2:
            pads.append(exporter.SmdPad(self.mapping[0], self.pad_size,
                                        np.array([-axis_offsets[0], 0.0])))
            pads.append(exporter.SmdPad(self.mapping[1], self.pad_size,
                                        np.array([axis_offsets[0], 0.0])))
        elif len(self.mapping) == 4:
            pads.append(exporter.SmdPad(self.mapping[0], self.pad_size,
                                        np.array([-axis_offsets[0], axis_offsets[1]])))
            pads.append(exporter.SmdPad(self.mapping[1], self.pad_size,
                                        np.array([axis_offsets[0], axis_offsets[1]])))
            pads.append(exporter.SmdPad(self.mapping[2], self.pad_size,
                                        np.array([axis_offsets[0], -axis_offsets[1]])))
            pads.append(exporter.SmdPad(self.mapping[3], self.pad_size,
                                        np.array([-axis_offsets[0], -axis_offsets[1]])))
        else:
            # Unsupported pin configuration
            raise ValueError()

        # First pin mark
        dot_mark_position = np.array([
            -(axis_offsets[0] + self.pad_size[0] / 2.0 + self.gap + self.thickness),
            axis_offsets[1]
        ])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0,
                                          self.thickness, True))

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
        return 'Quartz crystal SMD {:s}x{:s} mm'.format(*body_size)


class CrystalTH(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=CrystalTH.describe(descriptor), spec=spec)

        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.inner_diameter = descriptor['pads']['drill']
        self.pad_size = np.array([
            descriptor['pads']['diameter'],
            descriptor['pads']['diameter']])
        self.body_size = np.array(descriptor['body']['size'])

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Horizontal offset of the first pin
        first_pin_offset = -float(self.count - 1) * self.pitch / 2.0
        for i in range(0, self.count):
            x_offset = first_pin_offset + self.pitch * i
            objects.append(exporter.HolePad(str(i + 1), self.pad_size, (x_offset, 0.0),
                self.inner_diameter))

        # Body outline
        arc_radius = self.body_size[1] / 2.0
        arc_offset = self.body_size[0] / 2.0 - arc_radius
        objects.append(exporter.Circle(np.array([-arc_offset, 0.0]), arc_radius.item(),
                                       self.thickness, False, (90.0, -90.0)))
        objects.append(exporter.Circle(np.array([arc_offset, 0.0]), arc_radius.item(),
                                       self.thickness, False, (-90.0, 90.0)))
        objects.append(exporter.Line(np.array([-arc_offset, arc_radius]),
                                     np.array([arc_offset, arc_radius]), self.thickness))
        objects.append(exporter.Line(np.array([-arc_offset, -arc_radius]),
                                     np.array([arc_offset, -arc_radius]), self.thickness))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


types = [CrystalSMD, CrystalTH]
