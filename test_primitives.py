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
from wrlconv import helpers
from wrlconv import model
from wrlconv import x3d_export

def compare_models(source_file, destination_data):
    with open('tests/' + source_file, 'rb') as source:
        source_data = source.read().decode('utf-8')
    return source_data == destination_data

def serialize_models(models, path, name):
    full_path = path / name
    x3d_export.store(models, full_path)
    with open(full_path, 'rb') as file:
        data = file.read().decode('utf-8')
    return data


class TestChips:
    FILE_CHIP_CAPS = 'test_chip_caps.x3d'
    FILE_CHIP_HP = 'test_chip_hp.x3d'
    FILE_CHIP_LP = 'test_chip_lp.x3d'

    @staticmethod
    def make_chip(path, name, edge_resolution, line_resolution):
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
        serialized = serialize_models(meshes, path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_chip_caps(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        box_size = (2.0, 1.5, 1.0)
        box_chamfer = 0.1

        cap_xp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=False,
            edge_resolution=edge_resolution[0],
            line_resolution=line_resolution[0],
            axis=0
        )
        cap_xn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=True,
            edge_resolution=edge_resolution[1],
            line_resolution=line_resolution[1],
            axis=0
        )
        cap_yp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=False,
            edge_resolution=edge_resolution[1],
            line_resolution=line_resolution[1],
            axis=1
        )
        cap_yn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=True,
            edge_resolution=edge_resolution[2],
            line_resolution=line_resolution[2],
            axis=1
        )
        cap_zp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=False,
            edge_resolution=edge_resolution[2],
            line_resolution=line_resolution[2],
            axis=2
        )
        cap_zn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            invert=True,
            edge_resolution=edge_resolution[0],
            line_resolution=line_resolution[0],
            axis=2
        )
        meshes = [cap_xp, cap_xn, cap_yp, cap_yn, cap_zp, cap_zn]
        serialized = serialize_models(meshes, path, name)
        assert compare_models(name, serialized) == True

    def test_make_chip_caps(self, tmp_path):
        TestChips.make_chip_caps(tmp_path, TestChips.FILE_CHIP_CAPS, (2, 3, 4), (1, 2, 3))

    def test_make_chip_hp(self, tmp_path):
        TestChips.make_chip(tmp_path, TestChips.FILE_CHIP_HP, 3, 3)

    def test_make_chip_lp(self, tmp_path):
        TestChips.make_chip(tmp_path, TestChips.FILE_CHIP_LP, 1, 1)


class TestHelpers:
    def test_bezier_weight(self):
        try:
            value = primitives.calc_bezier_weight((1.0, 0.0, 0.0), None, None)
        except TypeError:
            value = None
        assert value == None

        try:
            value = primitives.calc_bezier_weight(None, (1.0, 0.0, 0.0), None)
        except TypeError:
            value = None
        assert value == None

        value = primitives.calc_bezier_weight((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), None)
        assert math.isclose(value, 0.5522847498307933) == True

        value = primitives.calc_bezier_weight(None, None, 1.5707963267948966)
        assert math.isclose(value, 0.5522847498307933) == True

    def test_hmils(self):
        value = primitives.hmils(2.54)
        assert math.isclose(value, 1.0) == True

        value = primitives.hmils(numpy.array([0.254, 1.27]))
        assert math.isclose(value[0], 0.1) == True
        assert math.isclose(value[1], 0.5) == True

    def test_median_point(self):
        try:
            value = primitives.calc_median_point([])
        except ValueError:
            value = None
        assert value == None

        value = primitives.calc_median_point([(1.0, 0.0, 0.0)])
        assert numpy.isclose(value, (1.0, 0.0, 0.0)).all() == True

        value = primitives.calc_median_point([(1.0, 1.0, 1.0), (-1.0, -1.0, -1.0)])
        assert numpy.isclose(value, (0.0, 0.0, 0.0)).all() == True

    def test_reverse_projection(self):
        try:
            value = primitives.reverse_projection((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        except ValueError:
            value = None
        assert value == None

    def test_round1f(self):
        value = primitives.round1f(1.0)
        assert value == '1'

        value = primitives.round1f(1.5)
        assert value == '1.5'

        value = primitives.round1f(1.75)
        assert value == '1.8'

    def test_round2f(self):
        value = primitives.round2f(1.0)
        assert value == '1.0'

        value = primitives.round2f(1.5)
        assert value == '1.5'

        value = primitives.round2f(1.09)
        assert value == '1.09'

        value = primitives.round2f(1.75)
        assert value == '1.75'

        value = primitives.round2f(1.875)
        assert value == '1.88'


class TestPins:
    FILE_BENT_PIN_HP = 'test_bent_pin_hp.x3d'
    FILE_BENT_PIN_LP = 'test_bent_pin_lp.x3d'
    FILE_FLAT_PIN_HP = 'test_flat_pin_hp.x3d'
    FILE_FLAT_PIN_LP = 'test_flat_pin_lp.x3d'

    @staticmethod
    def make_bent_pin(path, name, chamfer_resolution, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_pin_mesh(
            pin_shape_size=numpy.array([0.5, 0.25]),
            pin_height=2.0,
            pin_length=4.0,
            pin_slope=numpy.deg2rad(20.0),
            end_slope=numpy.deg2rad(10.0),
            chamfer_resolution=chamfer_resolution,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            flat=False
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_flat_pin(path, name, chamfer_resolution, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_pin_mesh(
            pin_shape_size=numpy.array([0.5, 0.25]),
            pin_height=2.0,
            pin_length=4.0,
            pin_slope=numpy.deg2rad(20.0),
            end_slope=numpy.deg2rad(10.0),
            chamfer_resolution=chamfer_resolution,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            flat=True
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    def test_make_bent_pin_hp(self, tmp_path):
        TestPins.make_bent_pin(tmp_path, TestPins.FILE_BENT_PIN_HP, 3, 3, 3)

    def test_make_bent_pin_lp(self, tmp_path):
        TestPins.make_bent_pin(tmp_path, TestPins.FILE_BENT_PIN_LP, 1, 1, 1)

    def test_make_flat_pin_hp(self, tmp_path):
        TestPins.make_flat_pin(tmp_path, TestPins.FILE_FLAT_PIN_HP, 3, 3, 3)

    def test_make_flat_pin_lp(self, tmp_path):
        TestPins.make_flat_pin(tmp_path, TestPins.FILE_FLAT_PIN_LP, 1, 1, 1)


class TestPrimitives:
    FILE_BODY_CAP = 'test_body_cap.x3d'
    FILE_LOFT_MESH = 'test_loft_mesh.x3d'
    FILE_SOLID_CAP = 'test_solid_cap.x3d'
    FILE_RECT_HALF = 'test_rect_half.x3d'
    FILE_ROTATION_MESH = 'test_rotation_mesh.x3d'

    @staticmethod
    def make_barrel_curve(radius, height, edge_resolution):
        curvature = radius / 5.0
        weight = primitives.calc_bezier_weight(angle=math.pi / 2.0)
        curve = []

        curve.append(curves.Line(
            (0.0, 0.0, 0.0),
            (radius - curvature, 0.0, 0.0),
            1
        ))
        curve.append(curves.Bezier(
            (radius - curvature, 0.0, 0.0),
            (curvature * weight, 0.0, 0.0),
            (radius, 0.0, curvature),
            (0.0, 0.0, -curvature * weight),
            edge_resolution
        ))
        curve.append(curves.Line(
            (radius, 0.0, curvature),
            (radius, 0.0, height - curvature),
            1
        ))
        curve.append(curves.Bezier(
            (radius, 0.0, height - curvature),
            (0.0, 0.0, curvature * weight),
            (radius - curvature, 0.0, height),
            (curvature * weight, 0.0, 0.0),
            edge_resolution
        ))
        curve.append(curves.Line(
            (radius - curvature, 0.0, height),
            (0.0, 0.0, height),
            1
        ))
        return curve

    def test_make_body_cap(self, tmp_path):
        name = TestPrimitives.FILE_BODY_CAP
        model.reset_allocator()

        corners = [
            numpy.array([ 1.0,  1.0, 0.0]),
            numpy.array([-1.0,  1.0, 0.0]),
            numpy.array([-1.0, -1.0, 0.0]),
            numpy.array([ 1.0, -1.0, 0.0])
        ]
        offset = numpy.array([0.25, 0.25])
        mesh = primitives.make_body_cap(corners, 0.5, offset, 24)

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) == True

    def test_make_loft_mesh(self, tmp_path):
        name = TestPrimitives.FILE_LOFT_MESH
        model.reset_allocator()

        path = [
            curves.Line(numpy.array([0.0, 0.0, -1.0]), numpy.array([0.0, 0.0, 1.0]), 2)
        ]
        path_points = []
        for element in path:
            path_points.extend(element.tessellate())
        path_points = curves.optimize(path_points)

        shape_dict = geometry.make_circle_outline(numpy.array([0.0, 0.0, 0.0]), 0.5, 12)
        shape_points = []
        for i in range(0, len(shape_dict)):
            shape_points.append(shape_dict[i])
        shape_points.reverse()
        shape_points.append(shape_points[0])

        slices = curves.loft(path=path_points, shape=shape_points)
        mesh = primitives.build_loft_mesh(slices, True, True)

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) == True

    def test_make_solid_cap(self, tmp_path):
        name = TestPrimitives.FILE_SOLID_CAP
        model.reset_allocator()

        corners = [
            numpy.array([ 1.0,  1.0, 0.0]),
            numpy.array([-1.0,  1.0, 0.0]),
            numpy.array([-1.0, -1.0, 0.0]),
            numpy.array([ 1.0, -1.0, 0.0])
        ]

        mesh = model.Mesh()
        vertices = geometry.make_bezier_quad_outline(corners)

        for i in range(0, len(vertices)):
            mesh.geo_vertices.append(vertices[i])
        primitives.append_solid_cap(mesh, vertices, origin=numpy.array([0.0, 0.0, -1.0]))

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) == True

    def test_make_rect_half(self, tmp_path):
        name = TestPrimitives.FILE_RECT_HALF
        model.reset_allocator()

        path_curve = curves.Line((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1)
        path_points = path_curve.tessellate()

        edge_resolution = 3
        rect_roundness = 0.1 / math.sqrt(2.0)
        rect_size = (0.25, 0.5)

        def make_mesh(rotate):
            shape_curve = primitives.make_rounded_rect_half(
                size=rect_size,
                rotate=rotate,
                roundness=rect_roundness,
                segments=edge_resolution
            )
            shape_points = []
            [shape_points.extend(element.tessellate()) for element in shape_curve]
            slices = curves.loft(path_points, shape_points)
            return primitives.build_loft_mesh(slices, not rotate, rotate)

        meshes = [make_mesh(False), make_mesh(True)]
        meshes[0].translate((0.0, 0.5, 0.0))
        meshes[1].translate((0.0, -0.5, 0.0))

        serialized = serialize_models(meshes, tmp_path, name)
        assert compare_models(name, serialized) == True

    def test_make_rotation_mesh(self, tmp_path):
        name = TestPrimitives.FILE_ROTATION_MESH
        model.reset_allocator()

        curve = TestPrimitives.make_barrel_curve(
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

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) == True


class TestBox:
    FILE_BANDED_BOX_HP = 'test_banded_box_hp.x3d'
    FILE_BANDED_BOX_LP = 'test_banded_box_lp.x3d'
    FILE_BANDED_BOX_MARK_HP = 'test_banded_box_mark_hp.x3d'
    FILE_BANDED_BOX_MARK_LP = 'test_banded_box_mark_lp.x3d'
    FILE_BARREL_BOX_HP = 'test_barrel_box_hp.x3d'
    FILE_BARREL_BOX_LP = 'test_barrel_box_lp.x3d'
    FILE_BOX_HP = 'test_box_hp.x3d'
    FILE_BOX_LP = 'test_box_lp.x3d'
    FILE_BOX_MARK_HP = 'test_box_mark_hp.x3d'
    FILE_BOX_MARK_LP = 'test_box_mark_lp.x3d'
    FILE_NONUNIFORM_BOX = 'test_nonuniform_box.x3d'

    @staticmethod
    def make_barrel_box(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_box(
            size=numpy.array([2.0, 2.0, 1.0]),
            chamfer=0.25,
            band_size=0.25,
            band_offset=0.0,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_box(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_box(
            size=numpy.array([2.0, 2.0, 2.0]),
            chamfer=0.25,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
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
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.25, mark_resolution)
        mark.translate(numpy.array([0.25, 0.25, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_banded_box(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_box(
            size=numpy.array([2.0, 2.0, 2.0]),
            chamfer=0.25,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.25
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_banded_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
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
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.25, mark_resolution)
        mark.translate(numpy.array([0.25, 0.25, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) == True

    def test_make_nonuniform_box(self, tmp_path):
        name = TestBox.FILE_NONUNIFORM_BOX
        model.reset_allocator()

        mesh = primitives.make_box(
            size=numpy.array([2.0, 2.0, 2.0]),
            chamfer=0.25,
            edge_resolution=3,
            line_resolution=(3, 2, 1)
        )

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) == True

    def test_make_barrel_box_hp(self, tmp_path):
        TestBox.make_barrel_box(tmp_path, TestBox.FILE_BARREL_BOX_HP, 3, 3)

    def test_make_barrel_box_lp(self, tmp_path):
        TestBox.make_barrel_box(tmp_path, TestBox.FILE_BARREL_BOX_LP, 1, 1)

    def test_make_box_hp(self, tmp_path):
        TestBox.make_box(tmp_path, TestBox.FILE_BOX_HP, 3, 3)

    def test_make_box_lp(self, tmp_path):
        TestBox.make_box(tmp_path, TestBox.FILE_BOX_LP, 1, 1)

    def test_make_box_mark_hp(self, tmp_path):
        TestBox.make_box_mark(tmp_path, TestBox.FILE_BOX_MARK_HP, 3, 3, 24)

    def test_make_box_mark_lp(self, tmp_path):
        TestBox.make_box_mark(tmp_path, TestBox.FILE_BOX_MARK_LP, 1, 1, 12)

    def test_make_banded_box_hp(self, tmp_path):
        TestBox.make_banded_box(tmp_path, TestBox.FILE_BANDED_BOX_HP, 3, 3)

    def test_make_banded_box_lp(self, tmp_path):
        TestBox.make_banded_box(tmp_path, TestBox.FILE_BANDED_BOX_LP, 1, 1)

    def test_make_banded_box_mark_hp(self, tmp_path):
        TestBox.make_banded_box_mark(tmp_path, TestBox.FILE_BANDED_BOX_MARK_HP, 3, 3, 24)

    def test_make_banded_box_mark_lp(self, tmp_path):
        TestBox.make_banded_box_mark(tmp_path, TestBox.FILE_BANDED_BOX_MARK_LP, 1, 1, 12)


class TestRoundedBox:
    FILE_ROUNDED_BOX_HP = 'test_rounded_box_hp.x3d'
    FILE_ROUNDED_BOX_LP = 'test_rounded_box_lp.x3d'
    FILE_ROUNDED_BOX_MARK_HP = 'test_rounded_box_mark_hp.x3d'
    FILE_ROUNDED_BOX_MARK_LP = 'test_rounded_box_mark_lp.x3d'

    @staticmethod
    def make_rounded_box(path, name, edge_resolution, line_resolution):
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

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    @staticmethod
    def make_rounded_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
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
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.25, mark_resolution)
        mark.translate(numpy.array([0.25, 0.25, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) == True

    def test_make_rounded_box_hp(self, tmp_path):
        TestRoundedBox.make_rounded_box(tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_HP, 3, 3)

    def test_make_rounded_box_lp(self, tmp_path):
        TestRoundedBox.make_rounded_box(tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_LP, 1, 1)

    def test_make_rounded_box_mark_hp(self, tmp_path):
        TestRoundedBox.make_rounded_box_mark(tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_MARK_HP,
                                             3, 3, 24)

    def test_make_rounded_box_mark_lp(self, tmp_path):
        TestRoundedBox.make_rounded_box_mark(tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_MARK_LP,
                                             1, 1, 12)


class TestSlopedBox:
    FILE_SLOPED_BOX_HP = 'test_sloped_box_hp.x3d'
    FILE_SLOPED_BOX_LP = 'test_sloped_box_lp.x3d'

    @staticmethod
    def make_sloped_box(path, name, edge_resolution, line_resolution):
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

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) == True

    def test_make_sloped_box_hp(self, tmp_path):
        TestSlopedBox.make_sloped_box(tmp_path, TestSlopedBox.FILE_SLOPED_BOX_HP, 3, 3)

    def test_make_sloped_box_lp(self, tmp_path):
        TestSlopedBox.make_sloped_box(tmp_path, TestSlopedBox.FILE_SLOPED_BOX_LP, 1, 1)
