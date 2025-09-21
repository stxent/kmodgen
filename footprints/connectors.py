#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# conncetors.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import numpy
import exporter
import primitives


class FFC(exporter.Footprint):
    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=FFC.describe(descriptor), spec=spec)

        try:
            self.body_size = numpy.array([
                descriptor['body']['width'],
                descriptor['body']['height']
            ])
            self.body_offset = numpy.array([
                0.0,
                descriptor['pads']['offset']
            ])
        except KeyError:
            self.body_size = None
            self.body_offset = None

        try:
            self.mount_pad_size = numpy.array([
                descriptor['pads']['mountWidth'],
                descriptor['pads']['mountHeight']
            ])
            self.mount_pad_spacing = numpy.array([
                descriptor['mount']['horizontalSpacing'],
                descriptor['mount']['verticalSpacing']
            ])
        except KeyError:
            self.mount_pad_size = None
            self.mount_pad_spacing = None

        self.signal_pad_size = numpy.array([
            descriptor['pads']['width'],
            descriptor['pads']['height']
        ])
        self.count = descriptor['pins']['count']
        self.pitch = descriptor['pins']['pitch']

        if 'inversion' in descriptor['pins'] and descriptor['pins']['inversion']:
            self.inversion = +1.0
        else:
            self.inversion = -1.0

    def generate(self):
        silkscreen, pads, cutouts = [], [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        total_pads_width = float(self.count - 1) * self.pitch

        # First pin mark
        dot_mark_position = numpy.array([
            (total_pads_width / 2.0) * self.inversion,
            -(self.signal_pad_size[1] / 2.0 + self.gap + self.thickness)
        ])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Signal pads
        for i in range(0, self.count):
            x_offset = (total_pads_width / 2.0 - i * self.pitch) * self.inversion
            pads.append(exporter.SmdPad(str(i + 1), self.signal_pad_size, (x_offset, 0.0)))

        # Mounting pads
        if self.mount_pad_size is not None:
            mount_pad_offset = numpy.array([total_pads_width / 2.0, 0.0]) + self.mount_pad_spacing
            pads.append(exporter.SmdPad('', self.mount_pad_size, mount_pad_offset * [+1, 1]))
            pads.append(exporter.SmdPad('', self.mount_pad_size, mount_pad_offset * [-1, 1]))
            cutouts.append(exporter.Cutout(
                numpy.array([total_pads_width, self.gap * 2.0]) + self.signal_pad_size, (0.0, 0.0)))

        # Body outline
        if self.body_size is not None and self.body_offset is not None:
            outline = exporter.Rect(self.body_size / 2.0 + self.body_offset,
                self.body_size / -2.0 + self.body_offset, self.thickness)

            process_func = lambda x: exporter.collide_line(x, pads + cutouts, self.thickness,
                self.gap)
            for line in outline.lines:
                silkscreen.extend(process_func(line))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        if 'description' in descriptor:
            return descriptor['description']

        pitch_str = primitives.round2f(descriptor['pins']['pitch'])
        try:
            style_str = '{:s} contact style, '.format(descriptor['pins']['style'])
        except KeyError:
            style_str = ''

        return 'FFC/FPC connector, {:s} mm pitch, surface mount, {:s}{:d} circuits'.format(
            pitch_str, style_str, descriptor['pins']['count'])


class IpxFootprint(exporter.Footprint):
    def __init__(self, spec, descriptor, core_size, core_offset, side_size, side_offset):
        super().__init__(name=descriptor['title'],
                         description='Miniature RF connector for high-frequency signals', spec=spec)

        self.core_offset, self.core_size = numpy.array(core_offset), numpy.array(core_size)
        self.side_offset, self.side_size = numpy.array(side_offset), numpy.array(side_size)
        self.body_size = numpy.array([descriptor['body']['width'], descriptor['body']['height']])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        pads.append(exporter.SmdPad('1', self.core_size, self.core_offset))
        pads.append(exporter.SmdPad('2', self.side_size,
            self.side_offset * numpy.array([+1.0, +1.0])))
        pads.append(exporter.SmdPad('2', self.side_size,
            self.side_offset * numpy.array([+1.0, -1.0])))

        # Body outline
        outline_delta_x = (self.body_size[0] - self.side_size[0] - self.thickness) / 2.0
        outline_delta_x = self.gap - outline_delta_x if outline_delta_x < self.gap else 0.0
        outline_size = numpy.array([
            self.body_size[0] / 2.0 + outline_delta_x,
            self.body_size[1] / 2.0])
        outline = exporter.Rect(outline_size, outline_size * -1.0, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        return silkscreen + pads


class IPX(IpxFootprint):
    def __init__(self, spec, descriptor):
        super().__init__(spec=spec, descriptor=descriptor, core_size=(1.0, 1.0),
                         core_offset=(1.5, 0.0), side_size=(2.2, 1.05),
                         side_offset=(0.0, 1.475))


class MemoryCard(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            super().__init__(number, (diameter, diameter), position, diameter,
                             exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                             exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=MemoryCard.describe(descriptor), spec=spec)

        self.signal_pad_count = 9
        self.signal_pad_size = numpy.array([0.7, 1.6])
        self.signal_pad_pitch = -1.1
        self.signal_pad_offset = numpy.array([2.25, -10.5])

        # Top left pad, top right pad, bottom left pad, bottom right pad
        self.mount_pad_sizes = ((1.2, 1.4), (1.6, 1.4), (1.2, 2.2), (1.2, 2.2))
        self.mount_pad_offsets = ((-7.75, -10.0), (6.85, -10.0), (-7.75, -0.4), (7.75, -0.4))

        self.mount_hole_diameter = 1.0
        self.mount_hole_offsets = ((-4.93, 0.0), (3.05, 0.0))

        self.body_size = numpy.array([14.7, 14.5])
        self.body_offset = numpy.array([0.0, -2.75])
        self.label_offset = numpy.array([0.0, -2.0])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # First pin mark
        dot_mark_position = self.signal_pad_offset - numpy.array([0.0, self.signal_pad_size[1] / 2.0
            + self.gap + self.thickness])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Mounting pads
        for i in range(0, len(self.mount_pad_sizes)):
            pads.append(exporter.SmdPad('', self.mount_pad_sizes[i], self.mount_pad_offsets[i]))

        # Mounting holes
        for i in range(0, len(self.mount_hole_offsets)):
            pads.append(MemoryCard.MountHole('', self.mount_hole_offsets[i],
                self.mount_hole_diameter))

        # Signal pads
        for i in range(0, self.signal_pad_count):
            x_offset = self.signal_pad_offset[0] + self.signal_pad_pitch * i
            y_offset = self.signal_pad_offset[1]
            pads.append(exporter.SmdPad(str(i + 1), self.signal_pad_size,
                                        numpy.array([x_offset, y_offset])))

        # Body outline
        top_corner = self.body_size / 2.0
        outline = exporter.Rect(top_corner + self.body_offset, -top_corner + self.body_offset,
            self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


class AngularSmaFootprint(exporter.Footprint):
    class SidePad(exporter.AbstractPad):
        def __init__(self, number, size, position, layer):
            super().__init__(number, size, position, 0.0,
                             exporter.AbstractPad.STYLE_RECT, exporter.AbstractPad.FAMILY_SMD,
                             layer, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor, space, inner_size, outer_size):
        super().__init__(name=descriptor['title'],
                         description=AngularSmaFootprint.describe(descriptor), spec=spec)

        self.space = space
        self.inner_size = numpy.array(inner_size)
        self.outer_size = numpy.array(outer_size)

    @staticmethod
    def make_poly_line(points, thickness, layer):
        if len(points) < 2:
            raise ValueError()
        lines = []
        for seg in range(0, len(points) - 1):
            lines.append(exporter.Line(points[seg], points[seg + 1], thickness, layer))
        return lines

    def generate(self):
        objects = []
        objects.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        objects.append(AngularSmaFootprint.SidePad('1', self.inner_size, (0.0, 0.0),
            exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad('2', self.outer_size, (self.space, 0.0),
            exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad('2', self.outer_size, (-self.space, 0.0),
            exporter.AbstractPad.LAYERS_FRONT))
        objects.append(AngularSmaFootprint.SidePad('2', self.outer_size, (self.space, 0.0),
            exporter.AbstractPad.LAYERS_BACK))
        objects.append(AngularSmaFootprint.SidePad('2', self.outer_size, (-self.space, 0.0),
            exporter.AbstractPad.LAYERS_BACK))

        # Body outline
        x_outline = self.gap + self.thickness / 2.0 + self.outer_size[0] / 2.0 + self.space
        y_bottom_outline = (self.inner_size[1] - self.thickness) / 2.0
        y_top_outline = -(self.inner_size[1] + self.thickness) / 2.0 - self.gap

        outline_points = [
            numpy.array([x_outline, y_bottom_outline]),
            numpy.array([x_outline, y_top_outline]),
            numpy.array([-x_outline, y_top_outline]),
            numpy.array([-x_outline, y_bottom_outline])
        ]
        objects.extend(AngularSmaFootprint.make_poly_line(outline_points, self.thickness,
            exporter.Layer.SILK_FRONT))
        objects.extend(AngularSmaFootprint.make_poly_line(outline_points, self.thickness,
            exporter.Layer.SILK_BACK))

        return objects

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


class SMA:
    def __init__(self, spec, descriptor):
        if descriptor['body']['angular']:
            self.impl = AngularSmaFootprint(spec=spec, descriptor=descriptor, space=2.65,
                                            inner_size=(1.5, 4.6), outer_size=(2.0, 4.6))
        else:
            raise ValueError() # TODO Add more variants

        self.name = self.impl.name
        self.description = self.impl.description
        self.model = self.impl.model

    def generate(self):
        return self.impl.generate()


class MiniUSB(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            super().__init__(number, (diameter, diameter), position, diameter,
                             exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                             exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=MiniUSB.describe(descriptor), spec=spec)

        self.pad_offset = 3.05
        self.pad_pitch = 0.8
        self.pad_size = numpy.array([2.3, 0.5])
        self.mount_pad_offset = 4.4
        self.front_mount_pad = -2.95
        self.back_mount_pad = 2.55
        self.mount_pad_size = numpy.array([2.5, 2.0])
        self.mount_hole_diameter = 0.9
        self.mount_hole_spacing = 2.2
        self.body_size = numpy.array([9.3, 7.7])
        self.body_offset = numpy.array([1.35, 0.0])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # First pin mark
        dot_mark_position = numpy.array([
            self.pad_offset + self.pad_size[0] / 2.0 + self.gap + self.thickness,
            -2.0 * self.pad_pitch])
        silkscreen.append(exporter.Circle(dot_mark_position, self.thickness / 2.0, self.thickness))

        # Pads
        for i in range(0, 5):
            y_offset = float(i - 2) * self.pad_pitch
            pads.append(exporter.SmdPad(str(i + 1), self.pad_size, (self.pad_offset, y_offset)))

        pads.append(exporter.SmdPad('', self.mount_pad_size,
            (self.back_mount_pad, self.mount_pad_offset)))
        pads.append(exporter.SmdPad('', self.mount_pad_size,
            (self.back_mount_pad, -self.mount_pad_offset)))
        pads.append(exporter.SmdPad('', self.mount_pad_size,
            (self.front_mount_pad, self.mount_pad_offset)))
        pads.append(exporter.SmdPad('', self.mount_pad_size,
            (self.front_mount_pad, -self.mount_pad_offset)))

        pads.append(MiniUSB.MountHole('', (0.0, self.mount_hole_spacing),
            self.mount_hole_diameter))
        pads.append(MiniUSB.MountHole('', (0.0, -self.mount_hole_spacing),
            self.mount_hole_diameter))

        edge_margin = numpy.array([self.thickness / 2.0, 0])
        top_corner = self.body_size / 2.0
        outline = exporter.Rect(top_corner - self.body_offset,
            edge_margin - top_corner - self.body_offset, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


class USBTypeC(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, size, hole):
            super().__init__(number, size, position, hole,
                             exporter.AbstractPad.STYLE_OVAL, exporter.AbstractPad.FAMILY_TH,
                             exporter.AbstractPad.LAYERS_BOTH, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=MiniUSB.describe(descriptor), spec=spec)

        self.pad_offset = 4.75
        self.pad_pitch_a = 0.5
        self.pad_pitch_b = 0.8
        self.pad_size_a = numpy.array([0.3, 1.14])
        self.pad_size_b = numpy.array([0.6, 1.14])
        self.pad_start_b = 3.2

        self.mount_hole_offset_a = 3.68
        self.mount_hole_spacing_a = 2.89
        self.mount_hole_diameter_a = 0.65

        self.mount_hole_offset_b = 4.18
        self.mount_hole_offset_c = 0.0
        self.mount_hole_spacing_b = 4.32
        self.mount_hole_size_b = numpy.array([1.0, 2.1])
        self.mount_hole_size_c = numpy.array([1.0, 1.8])
        self.mount_hole_b = numpy.array([0.6, 1.7])
        self.mount_hole_c = numpy.array([0.6, 1.4])

        self.body_size = numpy.array([8.94, 7.4])
        self.body_offset = numpy.array([0.0, 1.05])

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Pads
        titles = ['B8', 'A5', 'B7', 'A6', 'A7', 'B6', 'A8', 'B5']
        for i in range(0, 8):
            x_offset = (float(i - 4) + 0.5) * self.pad_pitch_a
            pads.append(exporter.SmdPad(titles[i], self.pad_size_a, (x_offset, -self.pad_offset)))

        titles_left = ['A1', 'A4']
        titles_right = ['B1', 'B4']
        for i in range(0, 2):
            x_offset = self.pad_start_b - float(i) * self.pad_pitch_b
            pads.append(exporter.SmdPad(titles_left[i], self.pad_size_b,
                (-x_offset, -self.pad_offset)))
            pads.append(exporter.SmdPad(titles_right[i], self.pad_size_b,
                (x_offset, -self.pad_offset)))

        pads.append(MiniUSB.MountHole('', (self.mount_hole_spacing_a, -self.mount_hole_offset_a),
            self.mount_hole_diameter_a))
        pads.append(MiniUSB.MountHole('', (-self.mount_hole_spacing_a, -self.mount_hole_offset_a),
            self.mount_hole_diameter_a))

        pads.append(USBTypeC.MountHole('SHIELD',
            (self.mount_hole_spacing_b, -self.mount_hole_offset_b),
            self.mount_hole_size_b, self.mount_hole_b))
        pads.append(USBTypeC.MountHole('SHIELD',
            (-self.mount_hole_spacing_b, -self.mount_hole_offset_b),
            self.mount_hole_size_b, self.mount_hole_b))

        pads.append(USBTypeC.MountHole('SHIELD',
            (self.mount_hole_spacing_b, -self.mount_hole_offset_c),
            self.mount_hole_size_c, self.mount_hole_c))
        pads.append(USBTypeC.MountHole('SHIELD',
            (-self.mount_hole_spacing_b, -self.mount_hole_offset_c),
            self.mount_hole_size_c, self.mount_hole_c))

        edge_margin = numpy.array([self.thickness / 2.0, 0])
        top_corner = self.body_size / 2.0
        outline = exporter.Rect(top_corner - self.body_offset,
            edge_margin - top_corner - self.body_offset, self.thickness)

        process_func = lambda x: exporter.collide_line(x, pads, self.thickness, self.gap)
        for line in outline.lines:
            silkscreen.extend(process_func(line))

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


class USB:
    def __init__(self, spec, descriptor):
        if descriptor['body']['type'] == 'c':
            self.impl = USBTypeC(spec, descriptor)
        elif descriptor['body']['size'] == 'mini' and descriptor['body']['type'] == 'b':
            self.impl = MiniUSB(spec, descriptor)
        else:
            raise ValueError() # TODO Add more variants

        self.name = self.impl.name
        self.description = self.impl.description
        self.model = self.impl.model

    def generate(self):
        return self.impl.generate()


class XT(exporter.Footprint):
    class MountHole(exporter.AbstractPad):
        def __init__(self, number, position, diameter):
            super().__init__(number, (diameter, diameter), position, diameter,
                             exporter.AbstractPad.STYLE_CIRCLE, exporter.AbstractPad.FAMILY_NPTH,
                             exporter.AbstractPad.LAYERS_NONE, exporter.AbstractPad.LAYERS_NONE)


    def __init__(self, spec, descriptor):
        super().__init__(name=descriptor['title'],
                         description=XT.describe(descriptor), spec=spec)

        self.body_size = numpy.array(descriptor['body']['size'])
        self.body_offset_from_pin = numpy.array(descriptor['body']['offset'])

        self.pin_count = descriptor['pins']['count']
        self.pin_pitch = descriptor['pins']['pitch']
        self.pad_size = numpy.array([
            descriptor['pads']['diameter'],
            descriptor['pads']['diameter']
        ])
        self.pad_hole = descriptor['pins']['drill']
        self.pad_offset = (self.pin_count - 1) * self.pin_pitch / 2.0

        self.mount_diameter = descriptor['mount']['drill']
        self.mount_pitch = descriptor['mount']['pitch']
        self.mount_offset_from_pin = descriptor['mount']['offset']
        self.mount_circle_width = descriptor['mount']['width']

    def generate(self):
        silkscreen, pads = [], []
        silkscreen.append(exporter.Label(self.name, (0.0, 0.0), self.thickness, self.font))

        # Mounting holes
        mount_holes = [
            numpy.array([self.mount_pitch / 2.0, self.mount_offset_from_pin]),
            numpy.array([-self.mount_pitch / 2.0, self.mount_offset_from_pin])
        ]
        pads.append(XT.MountHole('', mount_holes[0], self.mount_diameter))
        pads.append(XT.MountHole('', mount_holes[1], self.mount_diameter))

        # Signal pads
        for i in range(0, self.pin_count):
            offset = self.pad_offset - self.pin_pitch * i
            style = exporter.AbstractPad.STYLE_RECT if i == 0 else exporter.AbstractPad.STYLE_CIRCLE
            pads.append(exporter.HolePad(str(i + 1), self.pad_size, (offset, 0.0), self.pad_hole, style))

        # Body outline
        body_offset = numpy.array([0.0, self.body_size[1] / 2.0 + self.body_offset_from_pin])
        top_corner = self.body_size[0:2] / 2.0

        polyline = []
        polyline.append(top_corner * numpy.array([-1.0, +1.0]) + body_offset)
        polyline.append(top_corner * numpy.array([+1.0, +1.0]) + body_offset)
        polyline.append(numpy.array([top_corner[0], mount_holes[0][1] + self.mount_diameter]))
        polyline.append(mount_holes[0] + numpy.array([self.mount_diameter, self.mount_diameter]))
        polyline.append(mount_holes[0] + numpy.array([self.mount_diameter, -self.mount_diameter]))
        polyline.append(numpy.array([top_corner[0], mount_holes[0][1] - self.mount_diameter]))
        polyline.append(top_corner * numpy.array([+1.0, -1.0]) + body_offset)
        polyline.append(top_corner * numpy.array([-1.0, -1.0]) + body_offset)
        polyline.append(numpy.array([-top_corner[0], mount_holes[1][1] - self.mount_diameter]))
        polyline.append(mount_holes[1] + numpy.array([-self.mount_diameter, -self.mount_diameter]))
        polyline.append(mount_holes[1] + numpy.array([-self.mount_diameter, self.mount_diameter]))
        polyline.append(numpy.array([-top_corner[0], mount_holes[1][1] + self.mount_diameter]))
        polyline.append(top_corner * numpy.array([-1.0, +1.0]) + body_offset)

        for i in range(0, len(polyline) - 1):
            line = exporter.Line(polyline[i], polyline[i + 1], self.thickness)
            silkscreen.append(line)

        return silkscreen + pads

    @staticmethod
    def describe(descriptor):
        return descriptor['description'] if 'description' in descriptor else ''


# Aliases

class EastRisingHB(FFC):
    pass


class EastRisingHT(FFC):
    pass


class Molex52271(FFC):
    pass


class Molex53261(FFC):
    pass


types = [
    FFC,
    IPX,
    MemoryCard,
    SMA,
    USB,
    XT,
    EastRisingHB,
    EastRisingHT,
    Molex52271,
    Molex53261
]
