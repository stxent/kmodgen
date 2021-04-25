#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# capacitors.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import re
import exporter


class RadialCapacitor(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=RadialCapacitor.describe(descriptor),
                         spec=spec)

        self.body_diameter = descriptor['body']['diameter']
        self.pad_drill = descriptor['pads']['drill']
        self.pad_size = (descriptor['pads']['diameter'], descriptor['pads']['diameter'])
        self.spacing = descriptor['pins']['spacing']

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        mark_offset_x = -self.body_diameter / 2.0 - self.thickness - self.gap - self.font / 2.0
        objects.append(exporter.String('+', (mark_offset_x, 0.0), self.thickness, self.font))

        circle_radius = self.body_diameter / 2.0 + self.thickness / 2.0
        objects.append(exporter.Circle((0.0, 0.0), circle_radius, self.thickness, (0.0, 360.0)))

        pin_offset_x = self.spacing / 2.0
        objects.append(exporter.HolePad('A', self.pad_size, (-pin_offset_x, 0.0), self.pad_drill,
            exporter.AbstractPad.STYLE_RECT))
        objects.append(exporter.HolePad('C', self.pad_size, (pin_offset_x, 0.0), self.pad_drill,
            exporter.AbstractPad.STYLE_CIRCLE))

        return objects

    @staticmethod
    def describe(descriptor):
        description = ''
        if re.search('A-', descriptor['title'], re.S) is not None:
            description += 'axial '
        if re.search('R-', descriptor['title'], re.S) is not None:
            description += 'radial '
        if re.search('CP-', descriptor['title'], re.S) is not None:
            description += 'polarized '
        description += 'capacitor, pin spacing {:.1f} mm, diameter {:d} mm, height {:d} mm'.format(
            descriptor['pins']['spacing'], int(descriptor['body']['diameter']),
            int(descriptor['body']['height']))
        description = description[0].upper() + description[1:]
        return description


types = [RadialCapacitor]
