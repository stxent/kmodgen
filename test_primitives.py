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
from wrlconv import geometry
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

    corners = [
        numpy.array([ 1.0,  1.0, 0.0]),
        numpy.array([-1.0,  1.0, 0.0]),
        numpy.array([-1.0, -1.0, 0.0]),
        numpy.array([ 1.0, -1.0, 0.0])
    ]
    offset = numpy.array([0.25, 0.25])
    mesh = primitives.make_body_cap(corners, 0.5, offset, 24)

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def make_barrel_box_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_box(
        size=numpy.array([2.0, 2.0, 1.0]),
        chamfer=0.25,
        band_size=0.25,
        band_offset=0.0,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_barrel_box():
    make_barrel_box_impl('test_barrel_box_hp.x3d', 3, 3)
    make_barrel_box_impl('test_barrel_box_lp.x3d', 1, 1)

def make_box_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_box():
    make_box_impl('test_box_hp.x3d', 3, 3)
    make_box_impl('test_box_lp.x3d', 1, 1)

def make_box_mark_impl(name, edge_resolution, line_resolution, mark_resolution):
    model.reset_allocator()

    body = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        mark_radius=0.25,
        mark_offset=numpy.array([0.25, 0.25]),
        mark_resolution=mark_resolution
    )
    mark = geometry.Circle(0.25, mark_resolution)
    mark.translate(numpy.array([0.25, 0.25, 1.0]))

    serialized = serialize_models([body, mark], name)
    assert compare_models(name, serialized) == True

def test_make_box_mark():
    make_box_mark_impl('test_box_mark_hp.x3d', 3, 3, 24)
    make_box_mark_impl('test_box_mark_lp.x3d', 1, 1, 12)

def make_banded_box_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        band_size=0.1,
        band_offset=0.25
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_banded_box():
    make_banded_box_impl('test_banded_box_hp_eq.x3d', 3, 3)
    make_banded_box_impl('test_banded_box_hp_gt.x3d', 3, 2)
    make_banded_box_impl('test_banded_box_hp_le.x3d', 3, 4)
    make_banded_box_impl('test_banded_box_lp.x3d', 1, 1)

def make_banded_box_mark_impl(name, edge_resolution, line_resolution, mark_resolution):
    model.reset_allocator()

    body = primitives.make_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        band_size=0.1,
        band_offset=-0.25,
        mark_radius=0.25,
        mark_offset=numpy.array([0.25, 0.25]),
        mark_resolution=mark_resolution
    )
    mark = geometry.Circle(0.25, mark_resolution)
    mark.translate(numpy.array([0.25, 0.25, 1.0]))

    serialized = serialize_models([body, mark], name)
    assert compare_models(name, serialized) == True

def test_make_banded_box_mark():
    make_banded_box_mark_impl('test_banded_box_mark_hp.x3d', 3, 3, 24)
    make_banded_box_mark_impl('test_banded_box_mark_lp.x3d', 1, 1, 12)

def make_rounded_box_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_rounded_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        roundness=0.5,
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        band_size=0.1,
        band_offset=0.25
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_rounded_box():
    make_rounded_box_impl('test_rounded_box_hp_eq.x3d', 3, 3)
    make_rounded_box_impl('test_rounded_box_hp_gt.x3d', 3, 2)
    make_rounded_box_impl('test_rounded_box_hp_le.x3d', 3, 4)
    make_rounded_box_impl('test_rounded_box_lp.x3d', 1, 1)

def make_rounded_box_mark_impl(name, edge_resolution, line_resolution, mark_resolution):
    model.reset_allocator()

    body = primitives.make_rounded_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        roundness=0.5,
        chamfer=0.25,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        band_size=0.1,
        band_offset=-0.25,
        mark_radius=0.25,
        mark_offset=numpy.array([0.25, 0.25]),
        mark_resolution=mark_resolution
    )
    mark = geometry.Circle(0.25, mark_resolution)
    mark.translate(numpy.array([0.25, 0.25, 1.0]))

    serialized = serialize_models([body, mark], name)
    assert compare_models(name, serialized) == True

def test_make_rounded_box_mark():
    make_rounded_box_mark_impl('test_rounded_box_mark_hp.x3d', 3, 3, 24)
    make_rounded_box_mark_impl('test_rounded_box_mark_lp.x3d', 1, 1, 12)

def make_sloped_box_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_sloped_box(
        size=numpy.array([2.0, 2.0, 2.0]),
        chamfer=0.25,
        slope=math.pi / 4.0,
        slope_height=0.5,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        band_size=0.1,
        band_offset=0.25
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_sloped_box():
    make_sloped_box_impl('test_sloped_box_hp_eq.x3d', 3, 3)
    make_sloped_box_impl('test_sloped_box_hp_gt.x3d', 3, 2)
    make_sloped_box_impl('test_sloped_box_hp_le.x3d', 3, 4)
    make_sloped_box_impl('test_sloped_box_lp.x3d', 1, 1)

def make_chip_impl(name, edge_resolution, line_resolution):
    model.reset_allocator()

    body_size = numpy.array([2.0, 1.0, 0.5])
    lead_width = 0.5
    body_chamfer = 0.1
    case_chamfer = body_chamfer / (2.0 * math.sqrt(2.0))

    lead_size = numpy.array([lead_width, body_size[1], body_size[2]])
    ceramic_size = numpy.array([
        body_size[0] - 2.0 * lead_width,
        body_size[1] - 2.0 * case_chamfer,
        body_size[2] - 2.0 * case_chamfer])

    leads = primitives.make_chip_leads(
        case_size=ceramic_size,
        lead_size=lead_size,
        case_chamfer=case_chamfer,
        lead_chamfer=body_chamfer,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )
    leads.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))
    body = primitives.make_chip_body(
        size=ceramic_size,
        chamfer=case_chamfer,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )
    body.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))

    meshes = [body, leads]
    serialized = serialize_models(meshes, name)
    assert compare_models(name, serialized) == True

def test_make_chip():
    make_chip_impl('test_chip_hp.x3d', 3, 3)
    make_chip_impl('test_chip_lp.x3d', 1, 1)

def make_bent_pin_impl(name, chamfer_resolution, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_pin_mesh(
        pin_shape_size=numpy.array([0.5, 0.25]),
        pin_height=2.0,
        pin_length=4.0,
        pin_slope=math.pi * (20.0 / 180.0),
        end_slope=math.pi * (10.0 / 180.0),
        chamfer_resolution=chamfer_resolution,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        flat=False
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_bent_pin():
    make_bent_pin_impl('test_bent_pin_hp.x3d', 3, 3, 3)
    make_bent_pin_impl('test_bent_pin_lp.x3d', 1, 1, 1)

def make_flat_pin_impl(name, chamfer_resolution, edge_resolution, line_resolution):
    model.reset_allocator()

    mesh = primitives.make_pin_mesh(
        pin_shape_size=numpy.array([0.5, 0.25]),
        pin_height=2.0,
        pin_length=4.0,
        pin_slope=math.pi * (20.0 / 180.0),
        end_slope=math.pi * (10.0 / 180.0),
        chamfer_resolution=chamfer_resolution,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        flat=True
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

def test_make_flat_pin():
    make_flat_pin_impl('test_flat_pin_hp.x3d', 3, 3, 3)
    make_flat_pin_impl('test_flat_pin_lp.x3d', 1, 1, 1)

def test_make_rotation_mesh():
    name = 'test_rotation_mesh.x3d'
    model.reset_allocator()

    curve = make_barrel_curve(
        radius=1.0,
        height=2.0,
        edge_resolution=3
    )
    slices = curves.rotate(
        curve=curve,
        axis=numpy.array([0.0, 0.0, 1.0]),
        edges=24    
    )
    mesh = curves.create_rotation_mesh(
        slices=slices,
        wrap=True,
        inverse=True
    )

    serialized = serialize_models([mesh], name)
    assert compare_models(name, serialized) == True

if __name__ == '__main__':
    test_make_body_cap()
    test_make_barrel_box()
    test_make_box()
    test_make_box_mark()
    test_make_banded_box()
    test_make_banded_box_mark()
    test_make_rounded_box()
    test_make_rounded_box_mark()
    test_make_sloped_box()
    test_make_chip()
    test_make_bent_pin()
    test_make_flat_pin()
    test_make_rotation_mesh()
