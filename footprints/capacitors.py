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
        exporter.Footprint.__init__(self, name=descriptor["title"], description=RadialCapacitor.describe(descriptor))
        self.diameter = descriptor["body"]["radius"] * 2.
        self.drill = descriptor["pads"]["drill"]
        self.spacing = descriptor["pins"]["spacing"]
        self.size = (descriptor["pads"]["size"], descriptor["pads"]["size"])
        self.thickness = spec["thickness"]
        self.font = spec["font"]
        self.gap = spec["gap"]

        self.objects.append(exporter.Label(name=descriptor["title"], position=(0.0, 0.0), thickness=self.thickness,
                font=self.font))

        self.generate()

    def generate(self):
        markX = -self.diameter / 2. - self.thickness - self.gap - self.font / 2.
        self.objects.append(exporter.String(value="+", position=(markX, 0.0), thickness=self.thickness, font=self.font))

        radius = self.diameter / 2. + self.thickness / 2.
        self.objects.append(exporter.Circle((0.0, 0.0), radius, self.thickness, (0.0, 360.0)))

        pinX = self.spacing / 2.
        self.objects.append(exporter.HolePad(1, self.size, (-pinX, 0.0), self.drill, exporter.AbstractPad.STYLE_RECT))
        self.objects.append(exporter.HolePad(2, self.size, (pinX, 0.0), self.drill, exporter.AbstractPad.STYLE_CIRCLE))
        
    @staticmethod
    def describe(descriptor):
        description = ""
        if re.search("A-", descriptor["title"], re.S) is not None:
            description += "axial "
        if re.search("R-", descriptor["title"], re.S) is not None:
            description += "radial "
        if re.search("CP-", descriptor["title"], re.S) is not None:
            description += "polarized "
        description += "capacitor, pin spacing %.1f mm, diameter %u mm, height %u mm" % (descriptor["pins"]["spacing"],
                int(descriptor["body"]["radius"] * 2.), int(descriptor["body"]["height"]))
        description = description[0].upper() + description[1:]
        return description


types = [RadialCapacitor]
