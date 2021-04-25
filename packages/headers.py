#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# headers.py
# Copyright (C) 2015 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import copy
import math
import re

from wrlconv import model
import primitives

# TODO Replace with is_close
def equals(a, b): # pylint: disable=invalid-name
    tolerance = 0.001
    return a - tolerance <= b <= a + tolerance

def lookup(mesh_list, mesh_name):
    for entry in mesh_list:
        if re.search(mesh_name, entry.ident, re.S) is not None:
            return entry
    raise Exception()


class PinHeader:
    @staticmethod
    def generate_header_body(materials, model_body, model_edge, model_pin, body_transform,
                             count, pitch, name):
        shift = pitch / 2.0 if count[1] > 1 else 0.0

        body = model.Mesh(name='{:s}_{:d}Body'.format(name, count[0] * count[1]))
        body.visual_appearance = model_body.appearance()

        pins = []
        for i in range(0, count[0]):
            if i == 0:
                segment = copy.deepcopy(model_edge)
                segment.rotate([0.0, 0.0, 1.0], math.pi)
            elif i == count[0] - 1:
                segment = copy.deepcopy(model_edge)
                segment.rotate([0.0, 0.0, 1.0], 0.0)
            else:
                segment = copy.deepcopy(model_body)
            segment.translate([float(i) * pitch, shift, 0.0])
            body.append(segment)

            pin = model.Mesh(parent=model_pin, name='{:s}_{:d}Pin{:d}'.format(name,
                count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, shift, 0.001])
            if 'Pin' in materials:
                pin.appearance().material = materials['Pin']
            pins.append(pin)

        body.transform = copy.deepcopy(body_transform)
        body.translate([0.0, 0.0, 0.001])
        body.optimize()
        if 'Body' in materials:
            body.appearance().material = materials['Body']

        return [body] + pins

    def generate(self, materials, templates, descriptor):
        transform = model.Transform()
        pitch200 = equals(descriptor['pins']['pitch'], 2.0)
        pitch254 = equals(descriptor['pins']['pitch'], 2.54)

        if not pitch200 and not pitch254:
            raise Exception()

        if descriptor['pins']['rows'] == 1:
            if pitch200:
                object_names = ['PatPLS2Body', 'PatPLS2EdgeBody', 'PatPLS2Pin']
            elif pitch254:
                object_names = ['PatPLSBody', 'PatPLSEdgeBody', 'PatPLSPin']
        elif descriptor['pins']['rows'] == 2:
            if pitch200:
                object_names = ['PatPLD2Body', 'PatPLD2EdgeBody', 'PatPLD2Pin']
            elif pitch254:
                object_names = ['PatPLDBody', 'PatPLDEdgeBody', 'PatPLDPin']
        else:
            raise Exception()

        reference_object = [lookup(templates, name).parent for name in object_names]

        return PinHeader.generate_header_body(
            materials,
            reference_object[0], reference_object[1], reference_object[2], transform,
            (descriptor['pins']['columns'], descriptor['pins']['rows']),
            primitives.hmils(descriptor['pins']['pitch']),
            descriptor['title'])


class Jumper(PinHeader):
    def generate(self, materials, templates, descriptor):
        objects = PinHeader.generate(self, materials, templates, descriptor)

        pitch200 = equals(descriptor['pins']['pitch'], 2.0)
        pitch254 = equals(descriptor['pins']['pitch'], 2.54)

        if pitch200:
            body = lookup(templates, 'PatPLS2Jumper').parent
        elif pitch254:
            body = lookup(templates, 'PatPLSJumper').parent
        else:
            raise Exception()

        return objects + [body]


class RightAnglePinHeader(PinHeader):
    def generate(self, materials, templates, descriptor):
        transform = model.Transform()
        pitch200 = equals(descriptor['pins']['pitch'], 2.0)
        pitch254 = equals(descriptor['pins']['pitch'], 2.54)

        if pitch200:
            transform.translate([0.0, -0.391, 0.3937])
            transform.rotate([1.0, 0.0, 0.0], math.pi / 2.0)
        elif pitch254:
            transform.translate([0.0, -0.557, 0.5])
            transform.rotate([1.0, 0.0, 0.0], math.pi / 2.0)
        else:
            raise Exception()

        if descriptor['pins']['rows'] == 1:
            if pitch200:
                object_names = ['PatPLS2Body', 'PatPLS2EdgeBody', 'PatPLS2RPin']
            elif pitch254:
                object_names = ['PatPLSBody', 'PatPLSEdgeBody', 'PatPLSRPin']
        elif descriptor['pins']['rows'] == 2:
            if pitch200:
                object_names = ['PatPLD2Body', 'PatPLD2EdgeBody', 'PatPLD2RPin']
            elif pitch254:
                object_names = ['PatPLDBody', 'PatPLDEdgeBody', 'PatPLDRPin']
        else:
            raise Exception()

        reference_object = [lookup(templates, name).parent for name in object_names]

        return self.generate_header_body(
            materials,
            reference_object[0], reference_object[1], reference_object[2], transform,
            (descriptor['pins']['columns'], descriptor['pins']['rows']),
            primitives.hmils(descriptor['pins']['pitch']),
            descriptor['title'])


class BoxHeader:
    @staticmethod
    def generate_header_body(materials, model_body, model_pin, count, length, pitch, name):
        default_width = primitives.hmils(20.34)
        delta = (length - default_width) / 2.0

        left_part, right_part = model.Transform(), model.Transform()
        left_part.translate([-delta, 0.0, 0.0])
        right_part.translate([delta, 0.0, 0.0])
        transforms = [model.Transform(), left_part, right_part]
        body = copy.deepcopy(model_body)
        body.apply_transform(transforms)
        body.translate([delta, pitch / 2.0, 0.001])
        if 'Body' in materials:
            body.appearance().material = materials['Body']

        pins = []
        for i in range(0, count[0]):
            pin = model.Mesh(parent=model_pin, name='{:s}_{:d}Pin{:d}'.format(name,
                count[0] * count[1], (i + 1)))
            pin.translate([float(i) * pitch, pitch / 2.0, 0.001])
            if 'Pin' in materials:
                pin.appearance().material = materials['Pin']
            pins.append(pin)

        return [body] + pins

    def generate(self, materials, templates, descriptor):
        if descriptor['pins']['rows'] != 2:
            raise Exception()
        if not equals(descriptor['pins']['pitch'], 2.54):
            raise Exception()

        bh_body = lookup(templates, 'PatBHBody').parent
        bh_pin = lookup(templates, 'PatBHPin').parent

        # Modified BH models
        regions = [
            (((0.7, 3.0, 4.0), (-2.5, -3.0, -0.5)), 1),
            (((6.5, 3.0, 4.0), ( 4.5, -3.0, -0.5)), 2)]

        bh_attributed_body = model.AttributedMesh(name='PatBHAttributed', regions=regions)
        bh_attributed_body.append(bh_body)
        bh_attributed_body.visual_appearance = bh_body.appearance()

        return BoxHeader.generate_header_body(
            materials,
            bh_attributed_body,
            bh_pin,
            (descriptor['pins']['columns'], descriptor['pins']['rows']),
            primitives.hmils(descriptor['body']['size'][0]),
            primitives.hmils(descriptor['pins']['pitch']),
            descriptor['title'])


types = [PinHeader, RightAnglePinHeader, BoxHeader, Jumper]
