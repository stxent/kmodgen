#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_bezier.py
# Copyright (C) 2026 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy as np

import bezier
from wrlconv import curves, model, x3d_export

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


class TestBezierObject:
    FILE_BEZIER_BOX_1 = 'test_bezier_box_1.x3d'
    FILE_BEZIER_BOX_2_FINE = 'test_bezier_box_2_fine.x3d'
    FILE_BEZIER_BOX_2_FLAT = 'test_bezier_box_2_flat.x3d'
    FILE_BEZIER_BOX_3 = 'test_bezier_box_3.x3d'
    FILE_BEZIER_BOX_4 = 'test_bezier_box_4.x3d'
    FILE_BEZIER_CUBE = 'test_bezier_cube.x3d'
    FILE_BEZIER_CUBE_PART = 'test_bezier_cube_part.x3d'
    FILE_BEZIER_PYRAMID_3C = 'test_bezier_pyramid_3c.x3d'
    FILE_BEZIER_PYRAMID_4C = 'test_bezier_pyramid_4c.x3d'

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
            np.array([ -x,   y,  -z])
        ]
        vertex_attributes = {
            8: {'inversion': True}
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
            [4, 5, 13, 12], [3, 4, 12, 11]
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
            np.array([ -x,   y,  -z])
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
    def make_bezier_box_4():
        # pylint: disable=invalid-name
        x, y, z = 1.0, 1.0, 1.0
        r = 0.3
        # pylint: enable=invalid-name

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
            np.array([ -x,  y, -z])
        ]
        vertex_attributes = {
            0: {'chamfer': r},
            1: {'chamfer': r},
            2: {'chamfer': r},
            3: {'chamfer': r},
            4: {'chamfer': {5: r, 7: r}},
            5: {'chamfer': {6: r, 4: r}},
            6: {'chamfer': {7: r, 5: r}},
            7: {'chamfer': {4: r, 6: r}}
        }
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
            chamfer=0.1,
            edge_resolution=5,
            line_resolution=3,
            vertex_attributes=vertex_attributes
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
            np.array([ -x,  y, -z])
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
    def make_bezier_cube_part():
        x, y, z = 1.0, 1.0, 1.0 # pylint: disable=invalid-name

        vertices = [
            # Offset 0
            np.array([  x,  y,   z]),
            np.array([  x, -y,   z]),
            np.array([ -x, -y,   z]),
            np.array([ -x,  y,   z]),

            # Offset 4
            np.array([  x,  y, 0.0]),
            np.array([  x, -y, 0.0]),
            np.array([ -x, -y, 0.0]),
            np.array([ -x,  y, 0.0]),

            # Offset 8
            np.array([  x,  y,  -z]),
            np.array([  x, -y,  -z]),
            np.array([ -x, -y,  -z]),
            np.array([ -x,  y,  -z])
        ]
        vertex_attributes = {
            8: {'discard': True},
            9: {'discard': True},
            10: {'discard': True},
            11: {'discard': True}
        }
        edges = [
            # Top
            [0, 1, 2, 3, 0],
            # Medium
            [4, 5, 6, 7, 4],
            # Bottom
            [8, 9, 10, 11, 8],
            # Sides
            [0, 4, 8], [1, 5, 9], [2, 6, 10], [3, 7, 11]
        ]
        faces = [
            # Top
            [3, 2, 1, 0],
            # Sides
            [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=5,
            line_resolution=3,
            vertex_attributes=vertex_attributes
        )
        return mesh_object.tessellate()

    @staticmethod
    def make_bezier_pyramid_3c():
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
    def make_bezier_pyramid_4c():
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
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_box_1()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_BOX_1)

    def test_bezier_box_2_fine(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_box_2(math.pi)
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_BOX_2_FINE)

    def test_bezier_box_2_flat(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_box_2(math.pi * (5.0 / 6.0))
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_BOX_2_FLAT)

    def test_bezier_box_3(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_box_3()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_BOX_3)

    def test_bezier_box_4(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_box_4()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_BOX_4)

    def test_bezier_cube(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_cube()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_CUBE)

    def test_bezier_cube_part(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_cube_part()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_CUBE_PART)

    def test_bezier_pyramid_3c(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_pyramid_3c()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_PYRAMID_3C)

    def test_bezier_pyramid_4c(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObject.make_bezier_pyramid_4c()
        verify_models([mesh], tmp_path, TestBezierObject.FILE_BEZIER_PYRAMID_4C)


class TestBezierObjectCurves:
    FILE_BEZIER_CORNER = 'test_bezier_corner.x3d'
    FILE_BEZIER_DRUM = 'test_bezier_drum.x3d'

    @staticmethod
    def make_bezier_corner():
        x, y, z = 1.0, 1.0, 1.0 # disable=invalid-name

        inner = weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        outer = inner * 1.5

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
    def make_bezier_drum():
        # disable=invalid-name
        r, z = 1.0, 1.0
        t = curves.calc_bezier_weight(angle=math.pi / 2.0)
        # enable=invalid-name

        vertices = [
            # Offset 0
            np.array([0.0, 0.0,  z]),
            np.array([  r, 0.0,  z]),
            np.array([0.0,   r,  z]),
            np.array([ -r, 0.0,  z]),
            np.array([0.0,  -r,  z]),

            # Offset 5
            np.array([0.0, 0.0, -z]),
            np.array([  r, 0.0, -z]),
            np.array([0.0,   r, -z]),
            np.array([ -r, 0.0, -z]),
            np.array([0.0,  -r, -z])
        ]
        vertex_attributes = {
            # Top
            1:  {'bezier': {2: np.array([0.0,   t, 0.0]), 4: np.array([0.0,  -t, 0.0])}},
            2:  {'bezier': {3: np.array([ -t, 0.0, 0.0]), 1: np.array([  t, 0.0, 0.0])}},
            3:  {'bezier': {4: np.array([0.0,  -t, 0.0]), 2: np.array([0.0,   t, 0.0])}},
            4:  {'bezier': {1: np.array([  t, 0.0, 0.0]), 3: np.array([ -t, 0.0, 0.0])}},
            # Bottom
            6:  {'bezier': {7: np.array([0.0,   t, 0.0]), 9: np.array([0.0,  -t, 0.0])}},
            7:  {'bezier': {8: np.array([ -t, 0.0, 0.0]), 6: np.array([  t, 0.0, 0.0])}},
            8:  {'bezier': {9: np.array([0.0,  -t, 0.0]), 7: np.array([0.0,   t, 0.0])}},
            9:  {'bezier': {6: np.array([  t, 0.0, 0.0]), 8: np.array([ -t, 0.0, 0.0])}}
        }
        edges = [
            # Top
            [1, 2, 3, 4, 1], [0, 1], [0, 2], [0, 3], [0, 4],
            # Bottom
            [6, 7, 8, 9, 6], [5, 6], [5, 7], [5, 8], [5, 9],
            # Sides
            [1, 6], [2, 7], [3, 8], [4, 9]
        ]
        edge_attributes = {
            (1, 6):  {'resolution': 1},
            (2, 7):  {'resolution': 1},
            (3, 8):  {'resolution': 1},
            (4, 9):  {'resolution': 1}
        }
        faces = [
            # Top
            [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1],
            # Bottom
            [7, 6, 5], [8, 7, 5], [9, 8, 5], [6, 9, 5],
            # Sides
            [6, 7, 2, 1], [7, 8, 3, 2], [8, 9, 4, 3], [9, 6, 1, 4]
        ]

        mesh_object = bezier.BezierObject(
            vertices=vertices,
            edges=edges,
            faces=faces,
            chamfer=0.2,
            sharpness=math.pi * (5.0 / 6.0),
            edge_resolution=5,
            line_resolution=10,
            vertex_attributes=vertex_attributes,
            edge_attributes=edge_attributes
        )
        return mesh_object.tessellate()

    def test_bezier_corner(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObjectCurves.make_bezier_corner()
        verify_models([mesh], tmp_path, TestBezierObjectCurves.FILE_BEZIER_CORNER)

    def test_bezier_drum(self, tmp_path):
        model.reset_allocator()
        mesh = TestBezierObjectCurves.make_bezier_drum()
        verify_models([mesh], tmp_path, TestBezierObjectCurves.FILE_BEZIER_DRUM)
