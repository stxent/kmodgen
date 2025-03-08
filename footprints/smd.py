#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter


class Chip(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=Chip.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.pitch = descriptor['pads']['pitch']
        self.mapping = descriptor['pads']['names'] if 'names' in descriptor['pads'] else ['1', '2']

        self.mark_arrow = descriptor['mark']['arrow'] if 'arrow' in descriptor['mark'] else False
        self.mark_bar = descriptor['mark']['bar'] if 'bar' in descriptor['mark'] else False
        self.mark_dot = descriptor['mark']['dot'] if 'dot' in descriptor['mark'] else False
        self.mark_wrap = descriptor['mark']['wrap'] if 'wrap' in descriptor['mark'] else False

        if 'vertical' in descriptor['mark']:
            self.mark_vertical = descriptor['mark']['vertical']
        else:
            self.mark_vertical = False

        self.centered_arrow, self.filled_arrow, self.verification = True, False, True

    def generate(self):
        return self.generate_compact()

    def generate_compact(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        center = (self.pitch + self.pad_size[0]) / 2.0

        if self.mark_arrow or self.mark_wrap:
            # Horizontal border
            horiz = (self.pitch - self.thickness) / 2.0 - self.gap
            # Vertical border
            vert = (self.pad_size[1] - self.thickness) / 2.0
        else:
            # Horizontal border
            horiz = self.body_size[0] / 2.0
            # Vertical border
            min_vert = (self.pad_size[1] + self.thickness) / 2.0 + self.gap
            min_line_vert = self.pad_size[1] / 2.0 + self.thickness + self.gap
            if min_vert < self.body_size[1] / 2.0 < min_line_vert:
                vert = min_line_vert
            elif self.body_size[1] / 2.0 < min_vert:
                vert = min_vert
            else:
                vert = self.body_size[1] / 2.0

        pads = []
        pads.append(exporter.SmdPad(self.mapping[0], self.pad_size, (-center, 0.0)))
        pads.append(exporter.SmdPad(self.mapping[1], self.pad_size, (center, 0.0)))

        if not self.mark_arrow:
            if self.mark_vertical:
                objects.append(exporter.Line((0, vert), (0, -vert), self.thickness))
            else:
                objects.append(exporter.Line((horiz, vert), (-horiz, vert), self.thickness))
                objects.append(exporter.Line((horiz, -vert), (-horiz, -vert), self.thickness))

        if not self.mark_arrow and not self.mark_wrap:
            lines = []
            lines.append(exporter.Line((horiz, vert), (horiz, -vert), self.thickness))
            lines.append(exporter.Line((-horiz, vert), (-horiz, -vert), self.thickness))

            process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
            for line in lines:
                objects.extend(process_func(line))

        if self.mark_dot and self.verification:
            dot_mark_offset = center + self.pad_size[0] / 2.0 + self.gap + self.thickness
            objects.append(exporter.Circle((-dot_mark_offset, 0.0),
                self.thickness / 2.0, self.thickness))

        if self.mark_bar:
            horiz_polar = horiz - self.thickness # Outer border without polarization
            points = [(-horiz, -vert), (-horiz, vert), (-horiz_polar, vert), (-horiz_polar, -vert)]
            objects.append(exporter.Line(points[0], points[1], self.thickness))
            objects.append(exporter.Line(points[2], points[3], self.thickness))
            objects.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        if self.mark_arrow:
            if self.centered_arrow:
                horiz_right, horiz_left = 0.5 * vert, -0.5 * vert
            else:
                horiz_right, horiz_left = horiz, horiz - vert

            objects.append(exporter.Line((-horiz_right, vert), (-horiz_right, -vert),
                self.thickness))
            points = [(-horiz_left, vert), (-horiz_left, -vert), (-horiz_right, 0)]
            objects.append(exporter.Line(points[1], points[2], self.thickness))
            objects.append(exporter.Line(points[2], points[0], self.thickness))
            if self.filled_arrow:
                objects.append(exporter.Line(points[0], points[1], self.thickness))
                objects.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        objects.extend(pads)
        return objects

    def generate_large(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        if self.mark_wrap:
            # Scale outline to pad size
            outline = numpy.array([self.pad_size[0] * 2.0 + self.pitch, self.pad_size[1]])
            body = numpy.maximum(self.body_size, outline)
        else:
            body = self.body_size

        center = self.pitch / 2.0 + self.pad_size[0] / 2.0
        offset = self.gap + self.thickness / 2.0

        horiz0 = self.pitch / 2.0 # Inner border
        horiz1 = body[0] / 2.0 + offset # Outer border without polarization
        horiz2 = horiz1 - self.thickness # Polarization line
        vert = body[1] / 2.0 + offset # Vertical border

        pads = []
        pads.append(exporter.SmdPad(self.mapping[0], self.pad_size, (-center, 0)))
        pads.append(exporter.SmdPad(self.mapping[1], self.pad_size, (center, 0)))
        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)

        lines = []
        # Right lines
        lines.append(exporter.Line((horiz0, vert), (horiz1, vert), self.thickness))
        lines.append(exporter.Line((horiz0, -vert), (horiz1, -vert), self.thickness))
        lines.append(exporter.Line((horiz1, vert), (horiz1, -vert), self.thickness))

        # Left lines
        lines.append(exporter.Line((-horiz0, vert), (-horiz1, vert), self.thickness))
        lines.append(exporter.Line((-horiz0, -vert), (-horiz1, -vert), self.thickness))
        if self.mark_arrow or self.mark_bar or self.mark_dot:
            lines.append(exporter.Line((-horiz2, vert), (-horiz2, -vert), self.thickness))
        lines.append(exporter.Line((-horiz1, vert), (-horiz1, -vert), self.thickness))

        for line in lines:
            objects.extend(process_func(line))

        objects.extend(pads)
        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None


class ChipArray(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=Chip.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.pad_size = numpy.array(descriptor['pads']['size'])
        self.count = descriptor['pins']['count']
        self.pitch = numpy.array(descriptor['pins']['pitch'])

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Horizontal offset to the first pin
        columns = self.count // 2
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


class DPAK(exporter.Footprint):
    class PadDesc:
        def __init__(self, number, position, pattern, side, descriptor=None):
            if descriptor is None and pattern is None:
                # Not enough information
                raise Exception()
            if number is None != position is None:
                raise Exception()

            if number is not None:
                self.number = number

            try:
                self.name = descriptor['name']
            except (KeyError, TypeError):
                if number is not None:
                    self.name = str(number)
                else:
                    self.name = None

            try:
                self.offset = numpy.array(descriptor['offset'])
            except (KeyError, TypeError):
                self.offset = pattern.offset if pattern is not None else numpy.zeros(2)

            try:
                self.size = numpy.array(descriptor['size'])
            except (KeyError, TypeError):
                self.size = pattern.size

            self.position = self.offset * [1, side]
            if position is not None:
                self.position += position

        @classmethod
        def make_pattern(cls, descriptor):
            if descriptor is None:
                raise Exception()

            return cls(None, None, None, 1, descriptor)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=DPAK.describe(descriptor),
                         model=DPAK.assign_model(descriptor), spec=spec)

        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.body_size = numpy.array(descriptor['body']['size'])

        try:
            pad_pattern = DPAK.PadDesc.make_pattern(descriptor['pads']['default'])
        except KeyError:
            pad_pattern = None

        self.pads = []

        for i, key in [(i, str(i)) for i in range(1, self.count + 1)]:
            if key in descriptor['pins'] and descriptor['pins'][key] is None:
                continue

            position_x = self.calc_pad_position_x(i - 1)

            try:
                self.pads.append(DPAK.PadDesc(i, [position_x, 0.0], pad_pattern, 1,
                    descriptor['pads'][key]))
            except KeyError:
                self.pads.append(DPAK.PadDesc(i, [position_x, 0.0], pad_pattern, 1))

        try:
            self.pads.append(DPAK.PadDesc(i, [0.0, 0.0], pad_pattern, -1,
                descriptor['pads']['heatsink']))
        except KeyError:
            pass


        lower_bound = min([pad.position[1] - pad.size[1] / 2.0 for pad in self.pads])
        lower_bound -= self.gap + self.thickness / 2.0
        lower_bound = min(-self.body_size[1] / 2.0, lower_bound)
        upper_bound = self.body_size[1] / 2.0

        # XXX
        # https://www.infineon.com/cms/en/product/packages/PG-TO252/PG-TO252-3-11/
        self.border_size = numpy.array([self.body_size[0], upper_bound - lower_bound])
        self.border_center = numpy.array([0.0, lower_bound + upper_bound])

    def calc_pad_position_x(self, number):
        if number >= self.count:
            raise Exception()
        return self.pitch * (number - (self.count - 1) / 2.0)

    def generate(self):
        objects, pads = [], []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Body outline
        outline = exporter.Rect(self.border_size / 2.0 + self.border_center,
            self.border_size / -2.0 + self.border_center, self.thickness)

        for entry in self.pads:
            pads.append(exporter.SmdPad(entry.name, entry.size, entry.position))

        pads.sort(key=lambda x: x.number)
        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)

        for line in outline.lines:
            objects.extend(process_func(line))
        objects.extend(pads)

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None

    @staticmethod
    def assign_model(descriptor):
        return descriptor['body']['model'] if 'model' in descriptor['body'] else None


class MELF(Chip):
    def __init__(self, spec, descriptor):
        descriptor['body']['size'] = numpy.array([
            descriptor['body']['length'],
            descriptor['body']['radius'] * 2.0])
        super().__init__(spec, descriptor)


class SOT(exporter.Footprint):
    class PadDesc:
        def __init__(self, number, position, side, pattern, descriptor=None):
            if descriptor is None and pattern is None:
                # Not enough information
                raise Exception()
            if number is None != position is None:
                raise Exception()

            if number is not None:
                self.number = number

            try:
                self.name = descriptor['name']
            except (KeyError, TypeError):
                if number is not None:
                    self.name = str(number)
                else:
                    self.name = None

            try:
                self.offset = numpy.array(descriptor['offset'])
            except (KeyError, TypeError):
                self.offset = pattern.offset if pattern is not None else numpy.zeros(2)

            try:
                self.size = numpy.array(descriptor['size'])
            except (KeyError, TypeError):
                self.size = pattern.size

            if position is not None:
                self.position = position + self.offset * [1, side]

        @classmethod
        def make_pattern(cls, descriptor):
            if descriptor is None:
                raise Exception()

            return cls(None, None, None, None, descriptor)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'], description=SOT.describe(descriptor),
                         model=SOT.assign_model(descriptor), spec=spec)

        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']
        self.body_size = numpy.array(descriptor['body']['size'])

        try:
            self.mark_dot = descriptor['mark']['dot']
        except KeyError:
            self.mark_dot = False
        try:
            self.mark_tri = descriptor['mark']['tri']
        except KeyError:
            self.mark_tri = False

        try:
            pad_pattern = SOT.PadDesc.make_pattern(descriptor['pads']['default'])
        except KeyError:
            pad_pattern = None

        self.pads = []

        for i, key in [(i, str(i)) for i in range(1, self.count + 1)]:
            if key in descriptor['pins'] and descriptor['pins'][key] is None:
                if key in descriptor['pads']:
                    # Pin deleted, pad is ignored
                    raise Exception()
                continue

            position = self.calc_pad_position(i - 1)
            side = self.calc_pad_side(i - 1)

            try:
                self.pads.append(SOT.PadDesc(i, position, side, pad_pattern,
                    descriptor['pads'][key]))
            except KeyError:
                self.pads.append(SOT.PadDesc(i, position, side, pad_pattern))

        # Vertical border
        lower_pads, upper_pads = [], []
        for pad in self.pads:
            if pad.number <= self.count // 2:
                lower_pads.append(pad)
            else:
                upper_pads.append(pad)

        lower_bound = min([pad.position[1] - pad.size[1] / 2.0 for pad in lower_pads])
        upper_bound = max([pad.position[1] + pad.size[1] / 2.0 for pad in upper_pads])
        lower_bound -= self.gap + self.thickness / 2.0
        upper_bound += self.gap + self.thickness / 2.0
        lower_bound = min(self.body_size[1] / 2.0, lower_bound)
        upper_bound = max(-self.body_size[1] / 2.0, upper_bound)

        self.border_size = numpy.array([self.body_size[0], lower_bound - upper_bound])
        self.border_center = numpy.array([0.0, lower_bound + upper_bound])

    def calc_pad_position(self, number):
        columns = self.count // 2
        position = numpy.array([
            self.pitch * (number % columns - (columns - 1) / 2.0),
            self.body_size[1] / 2.0])
        return position * self.calc_pad_side(number)

    def calc_pad_side(self, number):
        return -1 if (number // (self.count // 2)) > 0 else 1

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Body outline
        silkscreen.append(exporter.Rect(self.border_size / 2.0 + self.border_center,
            self.border_size / -2.0 + self.border_center, self.thickness))

        # Outer polarity mark
        if self.mark_dot:
            # Assume that it is at least one pin at lower side
            first_pad = self.pads[0]
            dot_mark_offset = (first_pad.position[0]
                               - (first_pad.size[0] / 2.0 + self.gap + self.thickness))
            silkscreen.append(exporter.Circle((dot_mark_offset, first_pad.position[1]),
                self.thickness / 2.0, self.thickness))

        # Inner polarity mark
        if self.mark_tri:
            tri_mark_offset = min(1.0, self.border_size[1] / 2.0)
            top_corner = self.border_size / 2.0 + self.border_center
            points = [
                (-top_corner[0], top_corner[1] - tri_mark_offset),
                (-top_corner[0], top_corner[1]),
                (-top_corner[0] + tri_mark_offset, top_corner[1])]
            silkscreen.append(exporter.Poly(points, self.thickness, exporter.Layer.SILK_FRONT))

        for entry in self.pads:
            pads.append(exporter.SmdPad(entry.name, entry.size, entry.position))

        pads.sort(key=lambda x: x.number)
        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else None

    @staticmethod
    def assign_model(descriptor):
        return descriptor['body']['model'] if 'model' in descriptor['body'] else None


class CDRH(Chip):
    pass


class ChipCapacitor(Chip):
    pass


class ChipFerrite(Chip):
    pass


class ChipInductor(Chip):
    pass


class ChipResistor(Chip):
    pass


class ChipShunt(Chip):
    pass


types = [
    Chip,
    ChipArray,
    DPAK,
    MELF,
    SOT,
    CDRH,
    ChipCapacitor,
    ChipFerrite,
    ChipInductor,
    ChipResistor,
    ChipShunt
]
