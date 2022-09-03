#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_primitives.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

import primitives
from wrlconv import curves
from wrlconv import model
from wrlconv import x3d_export

def make_barrel_curve(radius, height, edge_resolution):
    curvature = radius / 5.0
    weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
    curve = []

    curve.append(curves.Line(
        (0.0, 0.0, 0.0),
        (radius - curvature, 0.0, 0.0),
        1))
    curve.append(curves.Bezier(
        (radius - curvature, 0.0, 0.0),
        (curvature * weight, 0.0, 0.0),
        (radius, 0.0, curvature),
        (0.0, 0.0, -curvature * weight),
        edge_resolution))
    curve.append(curves.Line(
        (radius, 0.0, curvature),
        (radius, 0.0, height - curvature),
        1))
    curve.append(curves.Bezier(
        (radius, 0.0, height - curvature),
        (0.0, 0.0, curvature * weight),
        (radius - curvature, 0.0, height),
        (curvature * weight, 0.0, 0.0),
        edge_resolution))
    curve.append(curves.Line(
        (radius - curvature, 0.0, height),
        (0.0, 0.0, height),
        1))

    return curve

def compare_models(source_file, destination_data):
    with open('tests/' + source_file, 'rb') as source:
        source_data = source.read().decode('utf-8')
    return source_data == destination_data

def serialize_models(models, filename):
    x3d_export.store(models, 'tmp/' + filename)
    with open('tmp/' + filename, 'rb') as file:
        data = file.read().decode('utf-8')
    return data

def test_make_body_cap():
    name = 'test_body_cap.x3d'
    model.reset_allocator()

    corners = [numpy.array([ 1.0,  1.0, 0.0]),
               numpy.array([-1.0,  1.0, 0.0]),
               numpy.array([-1.0, -1.0, 0.0]),
               numpy.array([ 1.0, -1.0, 0.0])]
    offset = numpy.array([0.25, 0.25])
    mesh = primitives.make_body_cap(corners, 0.5, offset, 24)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_box():
    name = 'test_box.x3d'
    model.reset_allocator()

    mesh, _ = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=3,
        line_resolution=2,
        band=0.1,
        band_width=0.1)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_box_mark():
    name = 'test_box_mark.x3d'
    model.reset_allocator()

    meshes = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=3,
        line_resolution=2,
        band=0.1,
        band_width=0.1,
        mark_radius=0.5,
        mark_offset=numpy.array([0.25, 0.25]),
        mark_resolution=24)

    serialized = serialize_models(meshes, name)
    assert compare_models(name, serialized) == True

def test_make_pin():
    name = 'test_pin.x3d'
    model.reset_allocator()

    mesh = primitives.make_pin_mesh(
        pin_shape_size=numpy.array([0.5, 0.25]),
        pin_height=2.0,
        pin_length=4.0,
        pin_slope=math.pi * (20.0 / 180.0),
        end_slope=math.pi * (10.0 / 180.0),
        chamfer_resolution=4,
        edge_resolution=3)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_rotation_mesh():
    name = 'test_rotation_mesh.x3d'
    model.reset_allocator()

    curve = make_barrel_curve(
        radius=1.0,
        height=2.0,
        edge_resolution=3)
    slices = curves.rotate(
        curve=curve,
        axis=numpy.array([0.0, 0.0, 1.0]),
        edges=24)
    mesh = curves.create_rotation_mesh(
        slices=slices,
        wrap=True,
        inverse=True)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_rounded_box():
    name = 'test_rounded_box.x3d'
    model.reset_allocator()

    mesh, _ = primitives.make_rounded_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        roundness=0.5,
        chamfer=0.25,
        edge_resolution=3,
        line_resolution=2,
        band=0.1,
        band_width=0.1)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_rounded_box_mark():
    name = 'test_rounded_box_mark.x3d'
    model.reset_allocator()

    meshes = primitives.make_rounded_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        roundness=0.5,
        chamfer=0.25,
        edge_resolution=3,
        line_resolution=2,
        band=0.1,
        band_width=0.1,
        mark_radius=0.5,
        mark_offset=numpy.array([0.25, 0.25]),
        mark_resolution=24)

    serialized = serialize_models(meshes, name)
    assert compare_models(name, serialized) == True

def test_make_sloped_box():
    name = 'test_sloped_box.x3d'
    model.reset_allocator()

    mesh = primitives.make_sloped_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        slope=math.pi / 4.0,
        slope_height=0.5,
        edge_resolution=3,
        line_resolution=2,
        band=0.1,
        band_width=0.1)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

if __name__ == '__main__':
    test_make_body_cap()
    test_make_box()
    test_make_box_mark()
    test_make_pin()
    test_make_rotation_mesh()
    test_make_rounded_box()
    test_make_rounded_box_mark()
    test_make_sloped_box()
