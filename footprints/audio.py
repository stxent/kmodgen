#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# audio.py
# Copyright (C) 2021 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import exporter


class Microphone(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=Microphone.describe(descriptor),
                         spec=spec)

        self.body_diameter = descriptor['body']['diameter']
        self.pad_drill = descriptor['pads']['drill']
        self.pad_size = (descriptor['pads']['diameter'], descriptor['pads']['diameter'])
        self.offset = descriptor['pins']['offset']
        self.spacing = descriptor['pins']['spacing']

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        circle_radius = self.body_diameter / 2.0 + self.thickness / 2.0
        objects.append(exporter.Circle((0.0, 0.0), circle_radius, self.thickness, (0.0, 360.0)))

        pin_offset_x, pin_offset_y = self.offset, self.spacing / 2.0
        objects.append(exporter.HolePad('1', self.pad_size, (pin_offset_x, pin_offset_y),
            self.pad_drill, exporter.AbstractPad.STYLE_RECT))
        objects.append(exporter.HolePad('2', self.pad_size, (pin_offset_x, -pin_offset_y),
            self.pad_drill, exporter.AbstractPad.STYLE_CIRCLE))

        return objects

    @staticmethod
    def describe(descriptor):
        return 'Microphone, diameter {:d} mm, height {:.1f} mm'.format(
            int(descriptor['body']['diameter']), descriptor['body']['height'])


types = [Microphone]
