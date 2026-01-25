#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_primitives.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy as np

import bezier
import primitives
from wrlconv import curves, geometry, helpers, model, x3d_export

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

        body_size = np.array([2.0, 1.0, 0.5])
        lead_width = 0.5
        body_chamfer = 0.1
        case_chamfer = body_chamfer / (2.0 * math.sqrt(2.0))

        lead_size = np.array([lead_width, body_size[1], body_size[2]])
        ceramic_size = np.array([
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
        leads.translate(np.array([0.0, 0.0, body_size[2] / 2.0]))
        body = primitives.make_chip_body(
            size=ceramic_size,
            chamfer=case_chamfer,
            edge_resolution=edge_resolution
        )
        body.translate(np.array([0.0, 0.0, body_size[2] / 2.0]))

        meshes = [body, leads]
        serialized = serialize_models(meshes, path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_chip_caps(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        box_size = (2.0, 1.5, 1.0)
        box_chamfer = 0.1

        cap_xp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=False,
            edge_resolution=edge_resolution[0],
            line_resolution=line_resolution[0],
            axis=0
        )
        cap_xn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=True,
            edge_resolution=edge_resolution[1],
            line_resolution=line_resolution[1],
            axis=0
        )
        cap_yp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=False,
            edge_resolution=edge_resolution[1],
            line_resolution=line_resolution[1],
            axis=1
        )
        cap_yn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=True,
            edge_resolution=edge_resolution[2],
            line_resolution=line_resolution[2],
            axis=1
        )
        cap_zp = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=False,
            edge_resolution=edge_resolution[2],
            line_resolution=line_resolution[2],
            axis=2
        )
        cap_zn = primitives.make_chip_lead_cap(
            size=box_size,
            chamfer=box_chamfer,
            inversion=True,
            edge_resolution=edge_resolution[0],
            line_resolution=line_resolution[0],
            axis=2
        )
        meshes = [cap_xp, cap_xn, cap_yp, cap_yn, cap_zp, cap_zn]
        serialized = serialize_models(meshes, path, name)
        assert compare_models(name, serialized) is True

    def test_make_chip_caps(self, tmp_path):
        TestChips.make_chip_caps(tmp_path, TestChips.FILE_CHIP_CAPS, (2, 3, 4), (1, 2, 3))

    def test_make_chip_hp(self, tmp_path):
        TestChips.make_chip(tmp_path, TestChips.FILE_CHIP_HP, 3, 3)

    def test_make_chip_lp(self, tmp_path):
        TestChips.make_chip(tmp_path, TestChips.FILE_CHIP_LP, 1, 1)


class TestHelpers:
    def test_bezier_weight(self):
        try:
            value = curves.calc_bezier_weight((1.0, 0.0, 0.0), None, None)
        except TypeError:
            value = None
        assert value is None

        try:
            value = curves.calc_bezier_weight(None, (1.0, 0.0, 0.0), None)
        except TypeError:
            value = None
        assert value is None

        value = curves.calc_bezier_weight((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), None)
        assert math.isclose(value, 0.5522847498307933) is True

        value = curves.calc_bezier_weight(None, None, 1.5707963267948966)
        assert math.isclose(value, 0.5522847498307933) is True

    def test_hmils(self):
        value = primitives.hmils(2.54)
        assert math.isclose(value, 1.0) is True

        value = primitives.hmils(np.array([0.254, 1.27]))
        assert math.isclose(value[0], 0.1) is True
        assert math.isclose(value[1], 0.5) is True

    def test_median_point(self):
        value = model.calc_median_point([])
        assert np.isclose(value, (0.0, 0.0, 0.0)).all().item() is True

        value = model.calc_median_point([(1.0, 0.0, 0.0)])
        assert np.isclose(value, (1.0, 0.0, 0.0)).all().item() is True

        value = model.calc_median_point([(1.0, 1.0, 1.0), (-1.0, -1.0, -1.0)])
        assert np.isclose(value, (0.0, 0.0, 0.0)).all().item() is True

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
            pin_shape_size=np.array([0.5, 0.3]),
            pin_height=2.0,
            pin_length=4.0,
            pin_slope=np.deg2rad(20.0),
            end_slope=np.deg2rad(10.0),
            chamfer_resolution=chamfer_resolution,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            flat=False
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_flat_pin(path, name, chamfer_resolution, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_pin_mesh(
            pin_shape_size=np.array([0.5, 0.3]),
            pin_height=2.0,
            pin_length=4.0,
            pin_slope=np.deg2rad(20.0),
            end_slope=np.deg2rad(10.0),
            chamfer_resolution=chamfer_resolution,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            flat=True
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

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
    FILE_ROTATION_CAP = 'test_rotation_cap.x3d'
    FILE_ROTATION_MESH = 'test_rotation_mesh.x3d'

    @staticmethod
    def make_barrel_curve(radius, height, edge_resolution, closed=True):
        curvature = radius / 5.0
        weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        curve = []

        if closed:
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
        if closed:
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
            np.array([ 1.0,  1.0, 0.0]),
            np.array([-1.0,  1.0, 0.0]),
            np.array([-1.0, -1.0, 0.0]),
            np.array([ 1.0, -1.0, 0.0])
        ]
        offset = np.array([0.2, 0.2])
        mesh = primitives.make_body_cap(corners, 0.5, offset, 24)

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_make_loft_mesh(self, tmp_path):
        name = TestPrimitives.FILE_LOFT_MESH
        model.reset_allocator()

        path = [
            curves.Line(np.array([0.0, 0.0, -1.0]), np.array([0.0, 0.0, 1.0]), 2)
        ]
        path_points = []
        for element in path:
            path_points.extend(element.tessellate())
        path_points = curves.optimize(path_points)

        shape_points = primitives.make_circle_outline(np.array([0.0, 0.0, 0.0]), 0.5, 12)
        shape_points.reverse()
        shape_points.append(shape_points[0])

        slices = curves.loft(path=path_points, shape=shape_points)
        mesh = geometry.build_loft_mesh(slices, True, True)

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_make_solid_cap(self, tmp_path):
        name = TestPrimitives.FILE_SOLID_CAP
        model.reset_allocator()

        corners = [
            np.array([ 1.0,  1.0, 0.0]),
            np.array([-1.0,  1.0, 0.0]),
            np.array([-1.0, -1.0, 0.0]),
            np.array([ 1.0, -1.0, 0.0])
        ]

        mesh = model.Mesh()
        vertices = primitives.make_bezier_quad_outline(corners)

        mesh.geo_vertices.extend(vertices)
        vertices_indexed = dict(zip(list(range(0, len(vertices))), vertices))
        primitives.append_solid_cap(mesh, vertices_indexed, origin=np.array([0.0, 0.0, -1.0]))

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_make_rect_half(self, tmp_path):
        name = TestPrimitives.FILE_RECT_HALF
        model.reset_allocator()

        path_curve = curves.Line((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1)
        path_points = path_curve.tessellate()

        edge_resolution = 3
        rect_roundness = 0.1 / math.sqrt(2.0)
        rect_size = (0.3, 0.5)

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
            return geometry.build_loft_mesh(slices, not rotate, rotate)

        meshes = [make_mesh(False), make_mesh(True)]
        meshes[0].translate((0.0, 0.5, 0.0))
        meshes[1].translate((0.0, -0.5, 0.0))

        serialized = serialize_models(meshes, tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_make_rotation_cap(self, tmp_path):
        name = TestPrimitives.FILE_ROTATION_CAP
        model.reset_allocator()

        curve = TestPrimitives.make_barrel_curve(
            radius=1.0,
            height=2.0,
            edge_resolution=3,
            closed=False
        )
        slices = curves.rotate(
            curve=curve,
            axis=np.array([0.0, 0.0, 1.0]),
            edges=24
        )

        beg_cap = primitives.make_rotation_cap_mesh(slices, True)
        end_cap = primitives.make_rotation_cap_mesh(slices, False)

        mesh = geometry.build_rotation_mesh(
            slices=slices,
            wrap=True,
            invert=True
        )
        mesh.append(beg_cap)
        mesh.append(end_cap)
        mesh.optimize()

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

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
            axis=np.array([0.0, 0.0, 1.0]),
            edges=24
        )
        mesh = geometry.build_rotation_mesh(
            slices=slices,
            wrap=True,
            invert=True
        )

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True


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
            size=np.array([2.0, 2.0, 1.0]),
            chamfer=0.2,
            band_size=0.2,
            band_offset=0.0,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_box(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
        model.reset_allocator()

        body = primitives.make_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2]),
            mark_resolution=mark_resolution
        )
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.3, mark_resolution)
        mark.translate(np.array([0.2, 0.2, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_banded_box(path, name, edge_resolution, line_resolution):
        model.reset_allocator()

        mesh = primitives.make_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.3
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_banded_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
        model.reset_allocator()

        body = primitives.make_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=-0.3,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2]),
            mark_resolution=mark_resolution
        )
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.3, mark_resolution)
        mark.translate(np.array([0.2, 0.2, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) is True

    def test_make_nonuniform_box(self, tmp_path):
        name = TestBox.FILE_NONUNIFORM_BOX
        model.reset_allocator()

        mesh = primitives.make_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=3,
            line_resolution=(3, 2, 1)
        )

        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

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
            size=np.array([2.0, 2.0, 2.0]),
            roundness=0.5,
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.3
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_rounded_box_mark(path, name, edge_resolution, line_resolution, mark_resolution):
        model.reset_allocator()

        body = primitives.make_rounded_box(
            size=np.array([2.0, 2.0, 2.0]),
            roundness=0.5,
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=-0.3,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2]),
            mark_resolution=mark_resolution
        )
        body.appearance().material = helpers.make_light_gray_material()

        mark = geometry.Circle(0.3, mark_resolution)
        mark.translate(np.array([0.2, 0.2, 1.0]))
        mark.appearance().material = helpers.make_dark_gray_material()

        serialized = serialize_models([body, mark], path, name)
        assert compare_models(name, serialized) is True

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
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            slope=math.pi / 4.0,
            slope_height=0.5,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.0
        )

        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    def test_make_sloped_box_hp(self, tmp_path):
        TestSlopedBox.make_sloped_box(tmp_path, TestSlopedBox.FILE_SLOPED_BOX_HP, 3, 3)

    def test_make_sloped_box_lp(self, tmp_path):
        TestSlopedBox.make_sloped_box(tmp_path, TestSlopedBox.FILE_SLOPED_BOX_LP, 1, 1)


class TestShapeScale:
    FILE_SHAPE_EQUALIZED = 'test_shape_equalized.x3d'
    FILE_SHAPE_SCALE_SIMPLE = 'test_shape_scale_simple.x3d'
    FILE_SHAPE_SCALE_SMART = 'test_shape_scale_smart.x3d'
    FILE_SHAPE_SCALE_SIMPLE_INV = 'test_shape_scale_simple_inv.x3d'
    FILE_SHAPE_SCALE_SMART_INV = 'test_shape_scale_smart_inv.x3d'

    @staticmethod
    def make_simple_scaled_rect(path, name, edge_resolution, line_resolution, inversion):
        def shift_slice(points, offset):
            return [point + np.array([0.0, 0.0, offset]) for point in points]

        model.reset_allocator()

        elements = primitives.make_rounded_rect(size=np.array([2.0, 1.0]), roundness=0.4,
                                                segments=edge_resolution,
                                                segments_line=line_resolution)
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        slices = []
        for i in range(-3, 4):
            points = primitives.simple_scale(shape, np.array([i * 0.07, i * 0.07, 0.0]))
            slices.append(shift_slice(points, 0.05 * (i + 3)))
        mesh = primitives.slice_connect_direct(slices, inversion)
        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    @staticmethod
    def make_smart_scaled_rect(path, name, edge_resolution, line_resolution, inversion):
        def shift_slice(points, offset):
            return [point + np.array([0.0, 0.0, offset]) for point in points]

        model.reset_allocator()

        elements = primitives.make_rounded_rect(size=np.array([2.0, 1.0]), roundness=0.1,
                                                segments=edge_resolution,
                                                segments_line=line_resolution)
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        slices = []
        for i in range(-3, 4):
            points = primitives.smart_scale(shape, i * 0.07)
            slices.append(shift_slice(points, 0.05 * (i + 3)))
        slices.append([np.array([0.0, 0.0, 6 * 0.05])])
        mesh = primitives.slice_connect_nearest(slices, inversion)
        serialized = serialize_models([mesh], path, name)
        assert compare_models(name, serialized) is True

    def test_equalized_rect(self, tmp_path):
        name = TestShapeScale.FILE_SHAPE_EQUALIZED
        model.reset_allocator()

        elements = primitives.make_rounded_rect(size=np.array([2.0, 1.0]), roundness=0.1,
                                                segments=3)
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        inner_circle = primitives.slice_equalize(shape, 0.3)
        slices = [shape, inner_circle]

        mesh = primitives.slice_connect_direct(slices, False)
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_simple_scale(self, tmp_path):
        TestShapeScale.make_simple_scaled_rect(tmp_path, TestShapeScale.FILE_SHAPE_SCALE_SIMPLE,
                                               5, 3, False)

    def test_smart_scale(self, tmp_path):
        TestShapeScale.make_smart_scaled_rect(tmp_path, TestShapeScale.FILE_SHAPE_SCALE_SMART,
                                              5, 3, False)

    def test_simple_scale_inversion(self, tmp_path):
        TestShapeScale.make_simple_scaled_rect(tmp_path, TestShapeScale.FILE_SHAPE_SCALE_SIMPLE_INV,
                                               5, 3, True)

    def test_smart_scale_inversion(self, tmp_path):
        TestShapeScale.make_smart_scaled_rect(tmp_path, TestShapeScale.FILE_SHAPE_SCALE_SMART_INV,
                                              5, 3, True)


class TestBezierObject:
    FILE_BEZIER_BOX_1 = 'test_bezier_box_1.x3d'
    FILE_BEZIER_BOX_2_FINE = 'test_bezier_box_2_fine.x3d'
    FILE_BEZIER_BOX_2_FLAT = 'test_bezier_box_2_flat.x3d'
    FILE_BEZIER_BOX_3 = 'test_bezier_box_3.x3d'
    FILE_BEZIER_CORNER = 'test_bezier_corner.x3d'
    FILE_BEZIER_CUBE = 'test_bezier_cube.x3d'
    FILE_BEZIER_PYRAMID = 'test_bezier_pyramid.x3d'
    FILE_BEZIER_PYRAMID_2 = 'test_bezier_pyramid_2.x3d'

    @staticmethod
    def make_bezier_box_1():
        x, y, z = 1.0, 1.0, 1.0 # pylint: disable=invalid-name

        vertices = [
            # Offset 0
            np.array([0.0,   y,   z]),
            np.array([0.0, 0.0,   z]),
            np.array([  x, 0.0,   z]),
            np.array([  x,  -y,   z]),
            np.array([ -x,  -y,   z]),
            np.array([ -x,   y,   z]),

            # Offset 6
            np.array([  x,   y, 0.0]),
            np.array([0.0,   y, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            np.array([  x, 0.0, 0.0]),

            # Offset 10
            np.array([  x,   y,  -z]),
            np.array([  x,  -y,  -z]),
            np.array([ -x,  -y,  -z]),
            np.array([ -x,   y,  -z]),
        ]
        vertex_attributes = {
            7: {'inversion': True},
            8: {'inversion': True},
            9: {'inversion': True}
        }
        edges = [
            # Top
            [0, 1, 2, 3, 4, 5, 0], [1, 4],
            # Medium
            [6, 7, 8, 9, 6],
            # Bottom
            [10, 11, 12, 13, 10],
            # Sides
            [3, 11], [4, 12], [5, 13],
            [0, 7], [1, 8], [2, 9],
            [6, 10], [7, 13], [9, 11]
        ]
        edge_attributes = {
            (1, 8): {'inversion': True},
            (7, 8): {'inversion': True},
            (8, 9): {'inversion': True}
        }
        faces = [
            [5, 0, 7, 13], [6, 10, 13, 7], [11, 9, 2, 3], [10, 6, 9, 11],
            # Top
            [1, 0, 5, 4],
            [4, 3, 2, 1],
            # Medium
            [6, 7, 8, 9],
            # Bottom
            [10, 11, 12, 13],
            # Sides
            [1, 8, 7, 0], [2, 9, 8, 1],
            [4, 5, 13, 12], [3, 4, 12, 11],
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            edge_resolution=5,
            line_resolution=3,
            vertex_attributes=vertex_attributes,
            edge_attributes=edge_attributes
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_box_2(sharpness):
        x, y, z = 1.0, 1.0, 1.0 # pylint: disable=invalid-name

        vertices = [
            # Offset 0
            np.array([  x,   y,   z]),
            np.array([  x,  -y,   z]),
            np.array([ -x,  -y,   z]),
            np.array([ -x,   y,   z]),

            # Offset 4
            np.array([  x * 1.1,   y * 1.1, 0.0]),
            np.array([  x * 1.1,  -y * 1.1, 0.0]),
            np.array([ -x * 1.1,  -y * 1.1, 0.0]),
            np.array([ -x * 1.1,   y * 1.1, 0.0]),

            # Offset 8
            np.array([  x,   y,  -z]),
            np.array([  x,  -y,  -z]),
            np.array([ -x,  -y,  -z]),
            np.array([ -x,   y,  -z]),
        ]
        edges = [
            # Horizontal
            [0, 1, 2, 3, 0],
            [4, 5, 6, 7, 4],
            [8, 9, 10, 11, 8],
            # Vertical
            [0, 4], [1, 5], [2, 6], [3, 7],
            [4, 8], [5, 9], [6, 10], [7, 11]
        ]
        faces = [
            # Top
            [3, 2, 1, 0],
            # Bottom
            [8, 9, 10, 11],
            # Sides
            [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
            [4, 5, 9, 8], [5, 6, 10, 9], [6, 7, 11, 10], [7, 4, 8, 11]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            sharpness=sharpness,
            edge_resolution=5,
            line_resolution=3
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_box_3():
        x, y, z = 1.0, 1.0, 1.0 # pylint: disable=invalid-name

        vertices = [
            # Offset 0
            np.array([  x, 0.0,   z]),
            np.array([  x,  -y,   z]),
            np.array([ -x,  -y,   z]),
            np.array([ -x, 0.0,   z]),

            # Offset 4
            np.array([  x,   y, 0.0]),
            np.array([ -x,   y, 0.0]),

            # Offset 6
            np.array([  x,   y,  -z]),
            np.array([  x,  -y,  -z]),
            np.array([ -x,  -y,  -z]),
            np.array([ -x,   y,  -z])
        ]
        edges = [
            # Horizontal
            [0, 1, 2, 3, 0],
            [4, 5],
            [6, 7, 8, 9, 6],
            # Vertical
            [0, 4], [3, 5],
            [4, 6], [5, 9],
            [1, 7], [2, 8],
            # Diagonal
            [6, 4], [3, 5],
            [4, 7], [5, 8]
        ]
        faces = [
            # Top
            [3, 2, 1, 0],
            [4, 5, 3, 0],
            # Bottom
            [6, 7, 8, 9],
            # Sides
            [1, 2, 8, 7],
            [6, 9, 5, 4],
            [7, 4, 0, 1], [7, 6, 4],
            [2, 3, 5, 8], [5, 9, 8]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            edge_resolution=5,
            line_resolution=3
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_corner():
        x, y, z = 1.0, 1.0, 1.0 # disable=invalid-name
        inner, outer = 1.0 * 0.553, 1.5 * 0.553

        vertices = [
            # Offset 0
            np.array([        x,  y,        z]),
            np.array([  x * 0.5,  y,        z]),
            np.array([  x * 0.5, -y,        z]),
            np.array([        x, -y,        z]),

            # Offset 4
            np.array([        x,  y,  z * 0.5]),
            np.array([  x * 0.5,  y,  z * 0.5]),
            np.array([  x * 0.5, -y,  z * 0.5]),
            np.array([        x, -y,  z * 0.5]),

            # Offset 8
            np.array([ -x * 0.5,  y,       -z]),
            np.array([ -x * 0.5,  y, -z * 0.5]),
            np.array([ -x * 0.5, -y, -z * 0.5]),
            np.array([ -x * 0.5, -y,       -z]),

            # Offset 12
            np.array([       -x,  y,       -z]),
            np.array([       -x,  y, -z * 0.5]),
            np.array([       -x, -y, -z * 0.5]),
            np.array([       -x, -y,       -z])
        ]
        vertex_attributes = {
            4:  {'bezier': { 8: np.array([  0.0, 0.0, -outer])}},
            5:  {'bezier': { 9: np.array([  0.0, 0.0, -inner])}},
            6:  {'bezier': {10: np.array([  0.0, 0.0, -inner])}},
            7:  {'bezier': {11: np.array([  0.0, 0.0, -outer])}},
            8:  {'bezier': { 4: np.array([outer, 0.0,    0.0])}},
            9:  {'bezier': { 5: np.array([inner, 0.0,    0.0])}},
            10: {'bezier': { 6: np.array([inner, 0.0,    0.0])}},
            11: {'bezier': { 7: np.array([outer, 0.0,    0.0])}}
        }
        edges = [
            # Top
            [0, 1, 2, 3, 0],
            [4, 5, 6, 7, 4],
            # Bottom
            [8, 9, 10, 11, 8],
            [12, 13, 14, 15, 12],
            # Sides
            [0, 4], [1, 5], [2, 6], [3, 7],
            [4, 8], [5, 9], [6, 10], [7, 11],
            [8, 12], [9, 13], [10, 14], [11, 15]
        ]
        edge_attributes = {
            (4, 8):  {'resolution': 10},
            (5, 9):  {'resolution': 10},
            (6, 10): {'resolution': 10},
            (7, 11): {'resolution': 10}
        }
        faces = [
            # Top
            [0, 1, 2, 3],
            # Bottom
            [15, 14, 13, 12],
            # Sides
            [4, 5, 1, 0], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3],
            [8, 9, 5, 4], [9, 10, 6, 5], [10, 11, 7, 6], [11, 8, 4, 7],
            [12, 13, 9, 8], [13, 14, 10, 9], [14, 15, 11, 10], [15, 12, 8, 11]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.1,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=5,
            line_resolution=3,
            vertex_attributes=vertex_attributes,
            edge_attributes=edge_attributes
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_cube():
        x, y, z = 1.0, 1.0, 1.0 # pylint: disable=invalid-name

        vertices = [
            # Offset 0
            np.array([  x,  y,  z]),
            np.array([  x, -y,  z]),
            np.array([ -x, -y,  z]),
            np.array([ -x,  y,  z]),

            # Offset 4
            np.array([  x,  y, -z]),
            np.array([  x, -y, -z]),
            np.array([ -x, -y, -z]),
            np.array([ -x,  y, -z]),
        ]
        edges = [
            # Top
            [0, 1, 2, 3, 0],
            # Bottom
            [4, 5, 6, 7, 4],
            # Sides
            [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        faces = [
            # Top
            [3, 2, 1, 0],
            # Bottom
            [4, 5, 6, 7],
            # Sides
            [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            edge_resolution=5,
            line_resolution=3
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_pyramid():
        # pylint: disable=invalid-name
        r, z = 1.0, 1.0
        a0, a1, a2 = 0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0
        # pylint: enable=invalid-name

        vertices = [
            np.array([             0.0,              0.0,   z]),
            np.array([math.cos(a0) * r, math.sin(a0) * r, 0.0]),
            np.array([math.cos(a1) * r, math.sin(a1) * r, 0.0]),
            np.array([math.cos(a2) * r, math.sin(a2) * r, 0.0])
        ]
        edges = [
            # Bottom
            [1, 2, 3, 1],
            # Sides
            [0, 1], [0, 2], [0, 3]
        ]
        faces = [
            [0, 1, 2], [0, 2, 3], [0, 3, 1], [3, 2, 1]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            edge_resolution=5,
            line_resolution=3
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_pyramid_2():
        # pylint: disable=invalid-name
        r, z = 1.0, 1.0
        # pylint: enable=invalid-name

        vertices = [
            np.array([0.0, 0.0,   z]),
            np.array([  r, 0.0, 0.0]),
            np.array([0.0,   r, 0.0]),
            np.array([ -r, 0.0, 0.0]),
            np.array([0.0,  -r, 0.0])
        ]
        edges = [
            # Bottom
            [1, 2, 3, 4, 1],
            # Sides
            [0, 1], [0, 2], [0, 3], [0, 4]
        ]
        faces = [
            [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1], [4, 3, 2, 1]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            edge_resolution=5,
            line_resolution=3
        )
        return mesh_object.tessellate()

    def test_bezier_box_1(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_BOX_1
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_box_1()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_box_2_fine(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_BOX_2_FINE
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_box_2(math.pi)
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_box_2_flat(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_BOX_2_FLAT
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_box_2(math.pi * (5.0 / 6.0))
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_box_3(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_BOX_3
        model.reset_allocator()

        mesh = mesh = TestBezierObject.make_bezier_box_3()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_corner(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_CORNER
        model.reset_allocator()
        
        mesh = mesh = TestBezierObject.make_bezier_corner()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_cube(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_CUBE
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_cube()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_pyramid(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_PYRAMID
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_pyramid()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True

    def test_bezier_pyramid_2(self, tmp_path):
        name = TestBezierObject.FILE_BEZIER_PYRAMID_2
        model.reset_allocator()

        mesh = TestBezierObject.make_bezier_pyramid_2()
        serialized = serialize_models([mesh], tmp_path, name)
        assert compare_models(name, serialized) is True
