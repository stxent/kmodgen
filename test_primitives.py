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

def verify_models(meshes, destination_path, source_name):
    serialized = serialize_models(meshes, destination_path, source_name)
    assert compare_models(source_name, serialized) is True


class TestChips:
    FILE_CHIP_CAPS = 'test_chip_caps.x3d'
    FILE_CHIP_HP = 'test_chip_hp.x3d'
    FILE_CHIP_LP = 'test_chip_lp.x3d'

    @staticmethod
    def make_chip(chamfer_resolution, edge_resolution, line_resolution):
        body_size = np.array([2.0, 1.0, 0.5])
        lead_width = 0.5
        lead_chamfer = 0.1
        body_chamfer = lead_chamfer / (2.0 * math.sqrt(2.0))

        lead_size = np.array([lead_width, body_size[1], body_size[2]])
        ceramic_size = np.array([
            body_size[0] - 2.0 * lead_width,
            body_size[1] - 2.0 * body_chamfer,
            body_size[2] - 2.0 * body_chamfer
        ])

        body, lead = primitives.make_chip(
            body_size=ceramic_size,
            lead_size=lead_size,
            body_chamfer=body_chamfer,
            lead_chamfer=lead_chamfer,
            chamfer_resolution=chamfer_resolution,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )
        lead.translate(np.array([0.0, 0.0, body_size[2] / 2.0]))
        body.translate(np.array([0.0, 0.0, body_size[2] / 2.0]))
        return [body, lead]

    @staticmethod
    def make_chip_caps(edge_resolution, line_resolution):
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
        return [cap_xp, cap_xn, cap_yp, cap_yn, cap_zp, cap_zn]

    def test_make_chip_caps(self, tmp_path):
        model.reset_allocator()
        meshes = TestChips.make_chip_caps((2, 3, 4), (1, 2, 3))
        verify_models(meshes, tmp_path, TestChips.FILE_CHIP_CAPS)

    def test_make_chip_hp(self, tmp_path):
        model.reset_allocator()
        meshes = TestChips.make_chip(2, 3, 3)
        verify_models(meshes, tmp_path, TestChips.FILE_CHIP_HP)

    def test_make_chip_lp(self, tmp_path):
        model.reset_allocator()
        meshes = TestChips.make_chip(1, 1, 1)
        verify_models(meshes, tmp_path, TestChips.FILE_CHIP_LP)


class TestChip:
    FILE_CHIP_HP = 'test_chip_hp.x3d'
    FILE_CHIP_LP = 'test_chip_lp.x3d'
    FILE_CHIP_SHUNT_HP = 'test_chip_shunt_hp.x3d'
    FILE_CHIP_SHUNT_LP = 'test_chip_shunt_lp.x3d'
    FILE_HOLLOW_PLANE = 'test_hollow_plane.x3d'
    FILE_HOLLOW_PLANE_ASYMMETRIC = 'test_hollow_plane_asymmetric.x3d'

    @staticmethod
    def make_chip_shunt(edge_resolution, line_resolution, slope_resolution):
        body, lead = primitives.make_chip_shunt(
            length=3.0,
            width=1.0,
            thickness=0.2,
            clearance=0.2,
            lead_length=0.4,
            active_width=0.8,
            chamfer=0.05,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            slope_resolution=slope_resolution
        )

        body.appearance().material = helpers.make_dark_gray_material()
        body.appearance().solid = True
        lead.appearance().material = helpers.make_light_gray_material()
        lead.appearance().solid = True

        return [body, lead]

    @staticmethod
    def make_hollow_plane(circle_resolution, plane_resolution, side_resolutions, inversion):
        # disable=invalid-name
        x, y = 1.0, 1.0
        w = 2.0 / 3.0
        # enable=invalid-name

        points = (
            np.array([ x,  y, 0.0]),
            np.array([ x, -y, 0.0]),
            np.array([-x, -y, 0.0]),
            np.array([-x,  y, 0.0])
        )
        controls = (
            (np.array([ -w, 0.0, 0.0]), np.array([0.0,  -w, 0.0])),
            (np.array([0.0,   w, 0.0]), np.array([ -w, 0.0, 0.0])),
            (np.array([  w, 0.0, 0.0]), np.array([0.0,   w, 0.0])),
            (np.array([0.0,  -w, 0.0]), np.array([  w, 0.0, 0.0]))
        )

        patches = primitives.make_hollow_plane(
            points=points,
            controls=controls,
            hollow_offset=np.array([0.5, 0.5, 0.0]),
            hollow_radius=0.2,
            circle_resolution=circle_resolution,
            plane_resolution=plane_resolution,
            side_resolutions=side_resolutions,
            inversion=inversion
        )

        plane, hole = bezier.patch_to_mesh(patches[0]), bezier.patch_to_mesh(patches[1])
        plane.appearance().material = helpers.make_light_gray_material()
        hole.appearance().material = helpers.make_dark_gray_material()

        return [plane, hole]

    def test_make_chip_shunt_hp(self, tmp_path):
        model.reset_allocator()
        meshes = TestChip.make_chip_shunt(3, 3, 5)
        verify_models(meshes, tmp_path, TestChip.FILE_CHIP_SHUNT_HP)

    def test_make_chip_shunt_lp(self, tmp_path):
        model.reset_allocator()
        meshes = TestChip.make_chip_shunt(1, 1, 1)
        verify_models(meshes, tmp_path, TestChip.FILE_CHIP_SHUNT_LP)

    def test_make_hollow_plane(self, tmp_path):
        model.reset_allocator()
        mesh_direct = TestChip.make_hollow_plane(24, 3, (2, 4), False)
        [mesh.translate(np.array([0.0, 0.0, 0.5])) for mesh in mesh_direct]
        mesh_inverted = TestChip.make_hollow_plane(12, 1, 1, True)
        [mesh.translate(np.array([0.0, 0.0, -0.5])) for mesh in mesh_inverted]
        verify_models(mesh_direct + mesh_inverted, tmp_path, TestChip.FILE_HOLLOW_PLANE)

    def test_make_hollow_plane_asymmetric(self, tmp_path):
        model.reset_allocator()
        mesh = TestChip.make_hollow_plane(24, 3, (2, 3, 4, 5), False)
        verify_models(mesh, tmp_path, TestChip.FILE_HOLLOW_PLANE_ASYMMETRIC)


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


class TestBentPins:
    FILE_BENT_PIN_HP = 'test_bent_pin_hp.x3d'
    FILE_BENT_PIN_LP = 'test_bent_pin_lp.x3d'
    FILE_BENT_FORK_PIN_HP = 'test_bent_fork_pin_hp.x3d'
    FILE_BENT_FORK_PIN_LP = 'test_bent_fork_pin_lp.x3d'

    @staticmethod
    def make_bent_pin(edge_resolution, line_resolution, slope_resolution):
        mesh = primitives.make_bent_pin_mesh(
            width=1.0,
            height=2.0,
            length=1.0,
            thickness=0.2,
            top_roundness=0.3,
            bottom_roundness=0.4,
            end_slope=np.deg2rad(10.0),
            chamfer=0.05,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            slope_resolution=slope_resolution
        )
        mesh.appearance().solid = True
        return mesh

    @staticmethod
    def make_bent_fork_pin(edge_resolution, line_resolution, slope_resolution):
        mesh = primitives.make_bent_fork_pin_mesh(
            width=1.0,
            height=2.0,
            length=1.0,
            thickness=0.2,
            top_roundness=0.3,
            bottom_roundness=0.4,
            end_slope=np.deg2rad(10.0),
            cutout_width=0.5,
            cutout_height=0.5,
            chamfer=0.05,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            slope_resolution=slope_resolution
        )
        mesh.appearance().solid = True
        return mesh

    def test_make_bent_pin_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBentPins.make_bent_pin(3, 3, 5)
        verify_models([mesh], tmp_path, TestBentPins.FILE_BENT_PIN_HP)

    def test_make_bent_pin_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBentPins.make_bent_pin(1, 1, 1)
        verify_models([mesh], tmp_path, TestBentPins.FILE_BENT_PIN_LP)

    def test_make_bent_fork_pin_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBentPins.make_bent_fork_pin(3, 3, 5)
        verify_models([mesh], tmp_path, TestBentPins.FILE_BENT_FORK_PIN_HP)

    def test_make_bent_fork_pin_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBentPins.make_bent_fork_pin(1, 1, 1)
        verify_models([mesh], tmp_path, TestBentPins.FILE_BENT_FORK_PIN_LP)


class TestPins:
    FILE_CURVED_PIN_HP = 'test_curved_pin_hp.x3d'
    FILE_CURVED_PIN_LP = 'test_curved_pin_lp.x3d'
    FILE_FLAT_PIN_HP = 'test_flat_pin_hp.x3d'
    FILE_FLAT_PIN_LP = 'test_flat_pin_lp.x3d'

    @staticmethod
    def make_curved_pin(edge_resolution, line_resolution, slope_resolution):
        mesh = primitives.make_pin_mesh(
            pin_shape_size=np.array([0.5, 0.3]),
            pin_height=2.0,
            pin_length=4.0,
            pin_slope=np.deg2rad(20.0),
            end_slope=np.deg2rad(10.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            slope_resolution=slope_resolution
        )
        mesh.appearance().solid = True
        return mesh

    @staticmethod
    def make_flat_pin(edge_resolution, line_resolution):
        mesh = primitives.make_flat_pin_mesh(
            pin_shape_size=np.array([0.5, 0.3]),
            pin_length=4.0,
            end_slope=np.deg2rad(10.0),
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )
        mesh.appearance().solid = True
        return mesh

    def test_make_curved_pin_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestPins.make_curved_pin(3, 3, 3)
        verify_models([mesh], tmp_path, TestPins.FILE_CURVED_PIN_HP)

    def test_make_curved_pin_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestPins.make_curved_pin(1, 1, 1)
        verify_models([mesh], tmp_path, TestPins.FILE_CURVED_PIN_LP)

    def test_make_flat_pin_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestPins.make_flat_pin(3, 3)
        verify_models([mesh], tmp_path, TestPins.FILE_FLAT_PIN_HP)

    def test_make_flat_pin_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestPins.make_flat_pin(1, 1)
        verify_models([mesh], tmp_path, TestPins.FILE_FLAT_PIN_LP)


class TestPrimitives:
    FILE_LOFT_MESH = 'test_loft_mesh.x3d'
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

    def test_make_loft_mesh(self, tmp_path):
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
        mesh.appearance().solid = True

        verify_models([mesh], tmp_path, TestPrimitives.FILE_LOFT_MESH)

    def test_make_rect_half(self, tmp_path):
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

        verify_models(meshes, tmp_path, TestPrimitives.FILE_RECT_HALF)

    def test_make_rotation_cap(self, tmp_path):
        model.reset_allocator()

        curve = TestPrimitives.make_barrel_curve(radius=1.0, height=2.0, edge_resolution=3,
                                                 closed=False)
        slices = curves.rotate(curve=curve, axis=np.array([0.0, 0.0, 1.0]), edges=24)

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
        mesh.appearance().solid = True

        verify_models([mesh], tmp_path, TestPrimitives.FILE_ROTATION_CAP)

    def test_make_rotation_mesh(self, tmp_path):
        model.reset_allocator()

        curve = TestPrimitives.make_barrel_curve(radius=1.0, height=2.0, edge_resolution=3)
        slices = curves.rotate(curve=curve, axis=np.array([0.0, 0.0, 1.0]), edges=24)

        mesh = geometry.build_rotation_mesh(slices=slices, wrap=True, invert=True)
        mesh.appearance().solid = True

        verify_models([mesh], tmp_path, TestPrimitives.FILE_ROTATION_MESH)


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
    FILE_NONUNIFORM_BOX_MARK = 'test_nonuniform_box_mark.x3d'

    @staticmethod
    def make_barrel_box(edge_resolution, line_resolution):
        body = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 1.0]),
            chamfer=0.2,
            band_size=0.2,
            band_offset=0.0,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )
        body.appearance().solid = True
        return body

    @staticmethod
    def make_box(edge_resolution, line_resolution):
        body = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )
        body.appearance().solid = True
        return body

    @staticmethod
    def make_box_mark(edge_resolution, line_resolution, mark_resolution):
        body, mark = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2, 0.0]),
            mark_resolution=mark_resolution
        )

        body.appearance().material = helpers.make_light_gray_material()
        body.appearance().solid = True
        mark.appearance().material = helpers.make_dark_gray_material()
        mark.appearance().solid = True

        return [body, mark]

    @staticmethod
    def make_banded_box(edge_resolution, line_resolution):
        body = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.3
        )
        body.appearance().solid = True
        return body

    @staticmethod
    def make_banded_box_mark(edge_resolution, line_resolution, mark_resolution):
        body, mark = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=-0.3,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2, 0.0]),
            mark_resolution=mark_resolution
        )

        body.appearance().material = helpers.make_light_gray_material()
        body.appearance().solid = True
        mark.appearance().material = helpers.make_dark_gray_material()
        mark.appearance().solid = True

        return [body, mark]

    @staticmethod
    def make_nonuniform_box():
        body = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=4,
            line_resolution=(3, 2, 1)
        )
        body.appearance().solid = True
        return body

    @staticmethod
    def make_nonuniform_box_mark():
        body, mark = primitives.make_box_with_mark(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            edge_resolution=4,
            line_resolution=(3, 2, 1),
            plane_resolution=5,
            mark_radius=0.3,
            mark_resolution=20
        )

        body.appearance().material = helpers.make_light_gray_material()
        body.appearance().solid = True
        mark.appearance().material = helpers.make_dark_gray_material()
        mark.appearance().solid = True

        return [body, mark]

    def test_make_barrel_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_barrel_box(3, 3)
        verify_models([mesh], tmp_path, TestBox.FILE_BARREL_BOX_HP)

    def test_make_barrel_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_barrel_box(1, 1)
        verify_models([mesh], tmp_path, TestBox.FILE_BARREL_BOX_LP)

    def test_make_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_box(3, 3)
        verify_models([mesh], tmp_path, TestBox.FILE_BOX_HP)

    def test_make_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_box(1, 1)
        verify_models([mesh], tmp_path, TestBox.FILE_BOX_LP)

    def test_make_box_mark_hp(self, tmp_path):
        model.reset_allocator()
        meshes = TestBox.make_box_mark(3, 3, 24)
        verify_models(meshes, tmp_path, TestBox.FILE_BOX_MARK_HP)

    def test_make_box_mark_lp(self, tmp_path):
        model.reset_allocator()
        meshes = TestBox.make_box_mark(1, 1, 12)
        verify_models(meshes, tmp_path, TestBox.FILE_BOX_MARK_LP)

    def test_make_banded_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_banded_box(3, 3)
        verify_models([mesh], tmp_path, TestBox.FILE_BANDED_BOX_HP)

    def test_make_banded_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_banded_box(1, 1)
        verify_models([mesh], tmp_path, TestBox.FILE_BANDED_BOX_LP)

    def test_make_banded_box_mark_hp(self, tmp_path):
        model.reset_allocator()
        meshes = TestBox.make_banded_box_mark(3, 3, 24)
        verify_models(meshes, tmp_path, TestBox.FILE_BANDED_BOX_MARK_HP)

    def test_make_banded_box_mark_lp(self, tmp_path):
        model.reset_allocator()
        meshes = TestBox.make_banded_box_mark(1, 1, 12)
        verify_models(meshes, tmp_path, TestBox.FILE_BANDED_BOX_MARK_LP)

    def test_make_nonuniform_box(self, tmp_path):
        model.reset_allocator()
        mesh = TestBox.make_nonuniform_box()
        verify_models([mesh], tmp_path, TestBox.FILE_NONUNIFORM_BOX)

    def test_make_nonuniform_box_mark(self, tmp_path):
        model.reset_allocator()
        meshes = TestBox.make_nonuniform_box_mark()
        verify_models(meshes, tmp_path, TestBox.FILE_NONUNIFORM_BOX_MARK)


class TestCarvedBox:
    FILE_CARVED_BOX_HP = 'test_carved_box_hp.x3d'
    FILE_CARVED_BOX_LP = 'test_carved_box_lp.x3d'

    @staticmethod
    def make_carved_box(edge_resolution, line_resolution):
        body = primitives.make_carved_box(
            size=np.array([2.0, 2.0, 2.0]),
            niche_size=np.array([0.6, 1.0, 0.6]),
            chamfer=0.2,
            roundness=0.4,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution
        )
        body.appearance().solid = True
        return body

    def test_make_carved_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestCarvedBox.make_carved_box(3, 3)
        verify_models([mesh], tmp_path, TestCarvedBox.FILE_CARVED_BOX_HP)

    def test_make_carved_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestCarvedBox.make_carved_box(1, 1)
        verify_models([mesh], tmp_path, TestCarvedBox.FILE_CARVED_BOX_LP)


class TestRoundedBox:
    FILE_ROUNDED_BOX_HP = 'test_rounded_box_hp.x3d'
    FILE_ROUNDED_BOX_LP = 'test_rounded_box_lp.x3d'
    FILE_ROUNDED_BOX_MARK_HP = 'test_rounded_box_mark_hp.x3d'
    FILE_ROUNDED_BOX_MARK_LP = 'test_rounded_box_mark_lp.x3d'

    @staticmethod
    def make_rounded_box(edge_resolution, line_resolution):
        body = primitives.make_rounded_box(
            size=np.array([2.0, 2.0, 2.0]),
            roundness=0.5,
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.3
        )
        body.appearance().solid = True
        return body

    @staticmethod
    def make_rounded_box_mark(edge_resolution, line_resolution, mark_resolution, plane_resolution):
        body, mark = primitives.make_rounded_box(
            size=np.array([2.0, 2.0, 2.0]),
            roundness=0.5,
            chamfer=0.2,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            plane_resolution=plane_resolution,
            band_size=0.1,
            band_offset=-0.3,
            mark_radius=0.3,
            mark_offset=np.array([0.2, 0.2, 0.0]),
            mark_resolution=mark_resolution
        )

        body.appearance().material = helpers.make_light_gray_material()
        body.appearance().solid = True
        mark.appearance().material = helpers.make_dark_gray_material()
        mark.appearance().solid = True

        return [body, mark]

    def test_make_rounded_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestRoundedBox.make_rounded_box(3, 3)
        verify_models([mesh], tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_HP)

    def test_make_rounded_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestRoundedBox.make_rounded_box(1, 1)
        verify_models([mesh], tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_LP)

    def test_make_rounded_box_mark_hp(self, tmp_path):
        model.reset_allocator()
        meshes = TestRoundedBox.make_rounded_box_mark(3, 3, 24, 2)
        verify_models(meshes, tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_MARK_HP)

    def test_make_rounded_box_mark_lp(self, tmp_path):
        model.reset_allocator()
        meshes = TestRoundedBox.make_rounded_box_mark(1, 1, 12, None)
        verify_models(meshes, tmp_path, TestRoundedBox.FILE_ROUNDED_BOX_MARK_LP)


class TestSlopedBox:
    FILE_SLOPED_BOX_HP = 'test_sloped_box_hp.x3d'
    FILE_SLOPED_BOX_LP = 'test_sloped_box_lp.x3d'

    @staticmethod
    def make_sloped_box(edge_resolution, line_resolution):
        body = primitives.make_sloped_box(
            size=np.array([2.0, 2.0, 2.0]),
            chamfer=0.2,
            slope=math.pi / 4.0,
            slope_height=0.5,
            edge_resolution=edge_resolution,
            line_resolution=line_resolution,
            band_size=0.1,
            band_offset=0.0
        )
        body.appearance().solid = True
        return body

    def test_make_sloped_box_hp(self, tmp_path):
        model.reset_allocator()
        mesh = TestSlopedBox.make_sloped_box(3, 3)
        verify_models([mesh], tmp_path, TestSlopedBox.FILE_SLOPED_BOX_HP)

    def test_make_sloped_box_lp(self, tmp_path):
        model.reset_allocator()
        mesh = TestSlopedBox.make_sloped_box(1, 1)
        verify_models([mesh], tmp_path, TestSlopedBox.FILE_SLOPED_BOX_LP)


class TestShapeScale:
    FILE_SHAPE_EQUALIZED = 'test_shape_equalized.x3d'
    FILE_SHAPE_SCALE_SIMPLE = 'test_shape_scale_simple.x3d'
    FILE_SHAPE_SCALE_SMART = 'test_shape_scale_smart.x3d'

    @staticmethod
    def make_equalized_rect():
        elements = primitives.make_rounded_rect(
            size=np.array([2.0, 1.0]),
            roundness=0.1,
            segments=3
        )
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        inner_circle = primitives.slice_equalize(shape, 0.3)
        slices = [shape, inner_circle]
        return primitives.slice_connect_direct(slices, False)

    @staticmethod
    def make_simple_scaled_rect(edge_resolution, line_resolution, inversion):
        def shift_slice(points, offset):
            return [point + np.array([0.0, 0.0, offset]) for point in points]

        elements = primitives.make_rounded_rect(
            size=np.array([2.0, 1.0]),
            roundness=0.4,
            segments=edge_resolution,
            segments_line=line_resolution
        )
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        slices = []
        for i in range(-3, 4):
            points = primitives.simple_scale(shape, np.array([i * 0.07, i * 0.07, 0.0]))
            slices.append(shift_slice(points, 0.05 * (i + 3)))
        return primitives.slice_connect_direct(slices, inversion)

    @staticmethod
    def make_smart_scaled_rect(edge_resolution, line_resolution, inversion):
        def shift_slice(points, offset):
            return [point + np.array([0.0, 0.0, offset]) for point in points]

        elements = primitives.make_rounded_rect(
            size=np.array([2.0, 1.0]),
            roundness=0.1,
            segments=edge_resolution,
            segments_line=line_resolution
        )
        shape = []
        [shape.extend(element.tessellate()) for element in elements]
        shape = curves.optimize(shape)

        slices = []
        for i in range(-3, 4):
            points = primitives.smart_scale(shape, i * 0.07)
            slices.append(shift_slice(points, 0.05 * (i + 3)))
        slices.append([np.array([0.0, 0.0, 6 * 0.05])])
        return primitives.slice_connect_nearest(slices, inversion)

    def test_equalized_rect(self, tmp_path):
        model.reset_allocator()
        mesh = TestShapeScale.make_equalized_rect()
        verify_models([mesh], tmp_path, TestShapeScale.FILE_SHAPE_EQUALIZED)

    def test_simple_scale(self, tmp_path):
        model.reset_allocator()
        mesh_direct = TestShapeScale.make_simple_scaled_rect(5, 3, False)
        mesh_direct.translate(np.array([0.0, 0.0, 0.5]))
        mesh_inverted = TestShapeScale.make_simple_scaled_rect(5, 3, True)
        mesh_inverted.translate(np.array([0.0, 0.0, -0.5]))
        verify_models([mesh_direct, mesh_inverted], tmp_path,
                      TestShapeScale.FILE_SHAPE_SCALE_SIMPLE)

    def test_smart_scale(self, tmp_path):
        model.reset_allocator()
        mesh_direct = TestShapeScale.make_smart_scaled_rect(5, 3, False)
        mesh_direct.translate(np.array([0.0, 0.0, 0.5]))
        mesh_inverted = TestShapeScale.make_smart_scaled_rect(5, 3, True)
        mesh_inverted.translate(np.array([0.0, 0.0, -0.5]))
        verify_models([mesh_direct, mesh_inverted], tmp_path,
                      TestShapeScale.FILE_SHAPE_SCALE_SMART)


class TestBezierSurfaces:
    FILE_SURFACE_QUAD_ASYMMETRIC = 'test_surface_quad_asymmetric.x3d'

    @staticmethod
    def make_surface_quad(resolution_u0, resolution_u1, resolution_v):
        # disable=invalid-name
        x, y = 2.0, 1.0
        wx, wy = x * 2.0 / 3.0, y * 2.0 / 3.0
        # enable=invalid-name

        points = (
            np.array([ x,  y, 0.0]),
            np.array([ x, -y, 0.0]),
            np.array([-x, -y, 0.0]),
            np.array([-x,  y, 0.0])
        )
        controls = (
            (np.array([-wx, 0.0, 0.0]), np.array([0.0, -wy, 0.0])),
            (np.array([0.0,  wy, 0.0]), np.array([-wx, 0.0, 0.0])),
            (np.array([ wx, 0.0, 0.0]), np.array([0.0,  wy, 0.0])),
            (np.array([0.0, -wy, 0.0]), np.array([ wx, 0.0, 0.0]))
        )

        lines = bezier.make_quad_lines(points, controls)
        patch = primitives.AsymmetricBezierQuad(*lines, resolution_u0, resolution_u1,
                                                resolution_v, False)
        return patch.tessellate()

    def test_surface_quad_asymmetric(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierSurfaces.make_surface_quad(2, 7, 5)
        verify_models([mesh], tmp_path, TestBezierSurfaces.FILE_SURFACE_QUAD_ASYMMETRIC)
