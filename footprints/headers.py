#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class PinHeader(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=PinHeader.describe(descriptor), spec=spec)

        self.count = numpy.array([descriptor['pins']['columns'], descriptor['pins']['rows']])
        self.pitch = descriptor['pins']['pitch']

        try:
            body_size_x = descriptor['body']['width']
        except KeyError:
            body_size_x = self.count[0] * self.pitch
        try:
            body_size_y = descriptor['body']['height']
        except KeyError:
            body_size_y = self.count[1] * self.pitch
        self.body_size = numpy.array([body_size_x, body_size_y])

        try:
            self.pad_offset = descriptor['pads']['offset']
        except KeyError:
            self.pad_offset = 0.0

        self.body_center = numpy.asarray(self.count - 1, dtype=numpy.float32)
        self.body_center = self.body_center * [1.0, -1.0] * (self.pitch / 2.0)
        self.pad_size = numpy.array([
            descriptor['pads']['diameter'],
            descriptor['pads']['diameter']
        ])
        self.pad_drill = descriptor['pads']['drill']

    def generate(self):
        label = exporter.Label(self.name, self.body_center, self.thickness, self.font)
        return [label] + self.generate_lines() + self.generate_pads()

    def generate_lines(self):
        objects = []

        outline_margin = self.pitch - 2.0 * self.gap - self.thickness
        outline_size = numpy.maximum(self.body_size,
                                     self.body_size + self.pad_size - outline_margin)
        objects.append(exporter.Rect(outline_size / 2.0 + self.body_center,
            -outline_size / 2.0 + self.body_center,
            self.thickness))

        return objects

    def generate_pads(self):
        objects = []

        for x_offset in range(0, self.count[0]):
            for y_offset in range(0, self.count[1]):
                number = 1 + x_offset * self.count[1] + y_offset
                if number == 1:
                    style = exporter.AbstractPad.STYLE_RECT
                else:
                    style = exporter.AbstractPad.STYLE_CIRCLE

                offset = numpy.array([float(x_offset), -float(y_offset)]) * self.pitch
                offset += numpy.array([0.0, self.pad_offset])
                objects.append(exporter.HolePad(number, self.pad_size, offset, self.pad_drill,
                    style))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None


class AngularPinHeader(PinHeader):
    def __init__(self, spec, descriptor):
        super().__init__(spec, descriptor)

        projection_length = descriptor['pins']['length'] - self.pitch / 2.0
        self.body_size += numpy.array([0.0, projection_length])
        self.body_center += numpy.array([0.0, projection_length / 2.0])

    def generate(self):
        objects = self.generate_pads()
        objects.append(exporter.Label(self.name, self.body_center, self.thickness, self.font))

        edge_margin = numpy.array([0, self.thickness / 2.0])
        outline_margin = self.pitch - 2.0 * self.gap - self.thickness
        outline_size = numpy.maximum(self.body_size,
                                     self.body_size + self.pad_size - outline_margin)
        line_offset_x = outline_size[0] / 2.0
        line_offset_y = numpy.maximum(self.pitch / 2.0,
                                      self.gap + (self.pad_size[1] + self.thickness) / 2.0)

        objects.append(exporter.Rect(outline_size / 2.0 + self.body_center - edge_margin,
            -outline_size / 2.0 + self.body_center, self.thickness))
        objects.append(exporter.Line((line_offset_x + self.body_center[0], line_offset_y),
            (-line_offset_x + self.body_center[0], line_offset_y), self.thickness))

        return objects


class BoxHeader(PinHeader):
    def __init__(self, spec, descriptor):
        super().__init__(spec, descriptor)
        self.body_size = numpy.array(descriptor['body']['size'])


class Jumper(PinHeader):
    pass


class ScrewTerminalBlock(PinHeader):
    pass


types = [PinHeader, AngularPinHeader, BoxHeader, Jumper, ScrewTerminalBlock]
