#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# different.py
# Copyright (C) 2024 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy as np
import exporter


class ESP32(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=ESP32.describe(descriptor), spec=spec)

        self.body_size = np.array(descriptor['body']['size'])
        self.cutout_height = descriptor['cutout']['height']
        self.pad_hor_offset = np.array(descriptor['pads']['hor_offset'])
        self.pad_ver_offset = descriptor['pads']['ver_offset']

        self.pad_size = np.array(descriptor['pads']['size'])
        self.pad_hor_count = descriptor['pins']['hor_count']
        self.pad_ver_count = descriptor['pins']['ver_count']
        self.pad_pitch = descriptor['pins']['pitch']

        self.power_pad_size = np.array(descriptor['heatsink']['size'])
        self.power_pad_offset = np.array(descriptor['heatsink']['offset'])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # First pin mark
        dot_mark_position = np.array([
            -(self.pad_hor_offset[0] + self.pad_size[1] / 2.0 + self.gap + self.thickness),
            self.pad_hor_offset[1]
        ])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0,
                                          self.thickness, True))

        # Antenna cutout area
        silkscreen.append(exporter.Line(
            np.array([-self.body_size[0] / 2.0, -self.body_size[1] / 2.0 + self.cutout_height]),
            np.array([self.body_size[0] / 2.0, -self.body_size[1] / 2.0 + self.cutout_height]),
            self.thickness
        ))

        # Signal pads, vertical rows
        for i in range(0, self.pad_ver_count):
            x_offset = self.pad_hor_offset[0]
            y_offset_left = self.pad_hor_offset[1] + i * self.pad_pitch
            y_offset_right = self.pad_hor_offset[1] + (self.pad_ver_count - i - 1) * self.pad_pitch
            size = np.array([self.pad_size[1], self.pad_size[0]])
            pads.append(exporter.SmdPad(str(i + 1), size,
                                        np.array([-x_offset, y_offset_left])))
            pads.append(exporter.SmdPad(str(self.pad_ver_count + self.pad_hor_count + i + 1), size,
                                        np.array([x_offset, y_offset_right])))

        # Signal pads, horizontal row
        for i in range(0, self.pad_hor_count):
            x_offset = -(self.pad_hor_count - 1) * self.pad_pitch / 2.0 + i * self.pad_pitch
            y_offset = self.pad_ver_offset
            size = self.pad_size
            pads.append(exporter.SmdPad(str(self.pad_ver_count + i + 1), size,
                                        np.array([x_offset, y_offset])))

        # Heatsink
        pads.append(exporter.SmdPad(str(self.pad_hor_count + self.pad_ver_count * 2 + 1),
                                    self.power_pad_size, self.power_pad_offset))

        # Body outline
        outline = exporter.Rect(self.body_size / 2.0, self.body_size / -2.0, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        pads.sort(key=lambda x: int(x.text))
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


types = [ESP32]
