#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# primitives.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy as np

import bezier
from wrlconv import curves
from wrlconv import geometry
from wrlconv import model


def hmils(values):
    # Convert millimeters to hundreds of mils
    try:
        return np.array([value / 2.54 for value in values])
    except TypeError:
        return values / 2.54


def round1f(value):
    if int(value * 10) == int(value) * 10:
        return f'{int(value):d}'
    return f'{value:.1f}'


def round2f(value):
    if int(value * 100) == int(value * 10) * 10:
        return f'{value:.1f}'
    return f'{value:.2f}'


class AsymmetricBezierQuad(curves.BezierQuad):
    def __init__(self, a, b, c, d, resolution_u0, resolution_u1, resolution_v,
                 inversion=False): # pylint: disable=invalid-name
        super().__init__(a, b, c, d, (max(resolution_u0, resolution_u1), resolution_v), inversion)

        if resolution_u0 < 1 or resolution_u1 < 1 or resolution_v < 1:
            raise ValueError()

        self.resolution_u0 = resolution_u0 + 1
        self.resolution_u1 = resolution_u1 + 1

    def tessellate(self):
        resolutions_u = np.linspace(self.resolution_u0, self.resolution_u1, self.resolution_v)
        points_v = np.linspace(0.0, 1.0, self.resolution_v)

        slices = []
        for i, resolution_raw in enumerate(resolutions_u):
            resolution = round(resolution_raw)
            points_u = np.linspace(0.0, 1.0, resolution)
            current = []
            for point in points_u:
                current.append(self.interpolate(points_v[i], point))
            slices.append(current)

        if self.resolution_u0 < self.resolution_u1:
            slices.reverse()
            self.inversion = not self.inversion

        return slice_connect_nearest(slices, self.inversion, False)


class CircularBezierQuad(curves.BezierQuad):
    def __init__(self, a, b, c, d, resolution, inversion=False): # pylint: disable=invalid-name
        super().__init__(a, b, c, d, resolution, inversion)

    def tessellate(self):
        points_u = np.linspace(0.0, 1.0, self.resolution_u)
        points_v = np.linspace(0.0, 1.0, self.resolution_v)
        side_0 = [self.interpolate(point, points_v[0]) for point in points_u[:-1]]
        side_1 = [self.interpolate(points_u[-1], point) for point in points_v[:-1]]
        side_2 = [self.interpolate(point, points_v[-1]) for point in points_u[:0:-1]]
        side_3 = [self.interpolate(points_u[0], point) for point in points_v[:0:-1]]
        vertices = side_0 + side_1 + side_2 + side_3
        mean = self.interpolate(0.5, 0.5)

        mesh = model.Mesh()
        mesh.geo_vertices.extend(vertices)
        mesh.geo_vertices.append(mean)
        mean_index = len(mesh.geo_vertices) - 1
        for i in range(mean_index):
            if self.inversion:
                mesh.geo_polygons.append([i, mean_index, (i + 1) % mean_index])
            else:
                mesh.geo_polygons.append([(i + 1) % mean_index, mean_index, i])
        return mesh


def make_bezier_quad_outline(points, resolution=(1, 1), roundness=1.0 / 3.0):
    p01_vec = (points[1] - points[0]) * roundness
    p03_vec = (points[3] - points[0]) * roundness
    p21_vec = (points[1] - points[2]) * roundness
    p23_vec = (points[3] - points[2]) * roundness

    p10_vec = -p01_vec
    p12_vec = -p21_vec
    p30_vec = -p03_vec
    p32_vec = -p23_vec

    side_a = curves.Bezier(points[0], p01_vec, points[1], p10_vec, resolution[0])
    side_b = curves.Bezier(points[1], p12_vec, points[2], p21_vec, resolution[1])
    side_c = curves.Bezier(points[2], p23_vec, points[3], p32_vec, resolution[0])
    side_d = curves.Bezier(points[3], p30_vec, points[0], p03_vec, resolution[1])

    vertices = []
    vertices.extend(side_a.tessellate())
    vertices.extend(side_b.tessellate())
    vertices.extend(side_c.tessellate())
    vertices.extend(side_d.tessellate())
    return vertices


def make_circle_outline(center, radius, edges):
    vertices = []
    angle, delta = 0.0, math.pi * 2.0 / edges

    for _ in range(edges):
        # pylint: disable=invalid-name
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        # pylint: enable=invalid-name

        vertices.append(center + np.array([x, y, 0.0]))
        angle += delta

    return vertices


def sort_vertices_by_angle(vertices, mean, normal, direction=None):
    keys = list(vertices.keys())

    if direction is None:
        direction = vertices[next(iter(vertices))] - mean

    angles = []
    for key in keys:
        vector = vertices[key] - mean
        angle = model.angle(direction, vector)
        if np.linalg.det(np.array([direction, vector, normal])) < 0.0:
            angle = -angle
        angles.append((key, angle))
    angles.sort(key=lambda x: x[1])

    return angles


def append_hollow_cap(mesh, outer, inner, normal):
    inner_mean = np.zeros(3)
    for vertex in inner.values():
        inner_mean += vertex
    inner_mean /= len(inner)

    direction = inner[next(iter(inner))] - inner_mean
    inner_indices = sort_vertices_by_angle(inner, inner_mean, normal, direction)
    outer_indices = sort_vertices_by_angle(outer, inner_mean, normal, direction)

    i_count, o_count = len(inner_indices), len(outer_indices)
    i_index, o_index = 0, 0
    i_offset = len(mesh.geo_vertices)
    polygons = []

    while o_index < o_count:
        if o_index < o_count - 1:
            threshold = (outer_indices[o_index + 1][1] + outer_indices[o_index][1]) / 2.0
        else:
            threshold = outer_indices[o_index][1]

        while i_index < i_count and (inner_indices[i_index][1] < threshold
                                     or o_index == o_count - 1):
            polygons.append([
                outer_indices[o_index][0],
                inner_indices[(i_index + 1) % i_count][0] + i_offset,
                inner_indices[i_index][0] + i_offset
            ])
            i_index += 1

        polygons.append([
            outer_indices[o_index][0],
            outer_indices[(o_index + 1) % o_count][0],
            inner_indices[i_index % i_count][0] + i_offset
        ])
        o_index += 1

    for vertex in inner.values():
        mesh.geo_vertices.append(vertex)
    mesh.geo_polygons.extend(polygons)


def append_solid_cap(mesh, vertices, origin=None, normal=None):
    if origin is None and normal is None:
        raise ValueError()

    mean = np.zeros(3)
    for vertex in vertices.values():
        mean += vertex
    mean /= len(vertices)

    if normal is None:
        normal = model.normalize(mean - origin)

    indices = [x[0] for x in sort_vertices_by_angle(vertices, mean, normal)]
    mean_index = len(mesh.geo_vertices)
    mesh.geo_vertices.append(mean)

    count = len(indices)
    polygons = []
    for i in range(count):
        polygons.append([indices[i % count], indices[(i + 1) % count], mean_index])
    mesh.geo_polygons.extend(polygons)


def make_hollow_plane(points, controls, hollow_offset, hollow_radius,
                      circle_resolution, plane_resolution, side_resolutions, inversion):
    if circle_resolution % 4 != 0:
        raise ValueError()
    if controls is None:
        controls = [(None, None)] * 4
    if isinstance(side_resolutions, int):
        side_resolutions = tuple(side_resolutions for _ in range(4))
    elif len(side_resolutions) == 2:
        side_resolutions = (*side_resolutions, *side_resolutions)
    elif len(side_resolutions) == 4:
        side_resolutions = tuple(side_resolutions)
    else:
        raise ValueError()

    default_tension = 1.0 / 3.0
    output_controls = []

    for b_key, b_pos in enumerate(points):
        a_key, c_key = b_key - 1, (b_key + 1) % len(points)
        current = controls[b_key]
        if current[0] is not None:
            ba_vec = current[0]
        else:
            ba_vec = (points[a_key] - b_pos) * default_tension
        if current[1] is not None:
            bc_vec = current[1]
        else:
            bc_vec = (points[c_key] - b_pos) * default_tension
        output_controls.append((ba_vec, bc_vec))

    dir_normal = model.normalize(np.cross(points[1] - points[0], points[3] - points[0]))
    dir_rotation = model.Transform()
    dir_rotation.rotate(dir_normal, math.pi / 4.0)
    dir_u = dir_rotation.apply(model.normalize(points[1] - points[0]))
    dir_v = dir_rotation.apply(model.normalize(points[3] - points[0]))

    hollow_center = sum(points) / 4.0 + hollow_offset
    hollow_points = [
        hollow_center - dir_u * hollow_radius,
        hollow_center - dir_v * hollow_radius,
        hollow_center + dir_u * hollow_radius,
        hollow_center + dir_v * hollow_radius
    ]
    hollow_vecs = [point - points[i] for i, point in enumerate(hollow_points)]

    cross_01 = curves.get_closest_point(hollow_points[0], dir_v, hollow_points[1], dir_u)
    cross_03 = curves.get_closest_point(hollow_points[0], dir_v, hollow_points[3], dir_u)
    cross_21 = curves.get_closest_point(hollow_points[2], dir_v, hollow_points[1], dir_u)
    cross_23 = curves.get_closest_point(hollow_points[2], dir_v, hollow_points[3], dir_u)
    weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
    hollow_controls = [
        ((hollow_points[0] - cross_01) * weight, (hollow_points[0] - cross_03) * weight),
        ((hollow_points[1] - cross_21) * weight, (hollow_points[1] - cross_01) * weight),
        ((hollow_points[2] - cross_23) * weight, (hollow_points[2] - cross_21) * weight),
        ((hollow_points[3] - cross_03) * weight, (hollow_points[3] - cross_23) * weight)
    ]

    plane_patches = []
    for i in range(len(points)):
        i_next = (i + 1) % len(points)
        patch_points = [points[i], points[i_next], hollow_points[i_next], hollow_points[i]]
        patch_controls = [
            (hollow_vecs[i] * default_tension, output_controls[i][1]),
            (output_controls[i_next][0], hollow_vecs[i_next] * default_tension),
            (-hollow_vecs[i_next] * default_tension, hollow_controls[i_next][0]),
            (hollow_controls[i][1], -hollow_vecs[i] * default_tension)
        ]
        patch_lines = bezier.make_quad_lines(patch_points, patch_controls)
        patch = AsymmetricBezierQuad(*patch_lines, side_resolutions[i], circle_resolution // 4,
                                     plane_resolution, inversion)
        plane_patches.append(patch)

    circle_lines = bezier.make_quad_lines(hollow_points, hollow_controls)
    circle_patch = CircularBezierQuad(*circle_lines, circle_resolution // 4, inversion)

    return (plane_patches, [circle_patch])


def make_rotation_cap_mesh(slices, inversion):
    if inversion:
        vertices = [slices[i][0] for i in range(len(slices))]
    else:
        vertices = [slices[i][-1] for i in range(len(slices))]

    indices = range(len(slices))
    geo_vertices = vertices + [sum(vertices) / len(slices)]
    geo_polygons = []

    if not inversion:
        for i, value in enumerate(indices):
            geo_polygons.append([len(vertices), value, indices[i - 1]])
    else:
        for i, value in enumerate(indices):
            geo_polygons.append([indices[i - 1], value, len(vertices)])

    # Generate object
    mesh = model.Mesh()
    mesh.geo_vertices = geo_vertices
    mesh.geo_polygons = geo_polygons
    return mesh


def make_box_with_mark(size, chamfer, edge_resolution, line_resolution, plane_resolution=None,
                       band_size=None, band_offset=0.0,
                       mark_radius=None, mark_offset=np.zeros(3), mark_resolution=24):
    try:
        resolutions = (line_resolution[0], line_resolution[1], line_resolution[2])
        default_resolution = max(resolutions) # TODO Select default resolution
    except TypeError:
        resolutions = (line_resolution, line_resolution, line_resolution)
        default_resolution = line_resolution
    if plane_resolution is None:
        plane_resolution = default_resolution

    x, y, z = np.array(size) / 2.0 # pylint: disable=invalid-name
    mark_patches = None

    def top_face_functor(points, controls, resolution, inversion):
        nonlocal mark_patches

        result = make_hollow_plane(
            points=points,
            controls=controls,
            hollow_offset=mark_offset,
            hollow_radius=mark_radius,
            circle_resolution=mark_resolution,
            plane_resolution=plane_resolution,
            side_resolutions=resolution,
            inversion=inversion
        )
        mark_patches = result[1]
        return result[0]

    vertices = [
        # Offset 0
        np.array([ x,  y, z]),
        np.array([-x,  y, z]),
        np.array([-x, -y, z]),
        np.array([ x, -y, z]),

        # Offset 4
        np.array([ x,  y, -z]),
        np.array([-x,  y, -z]),
        np.array([-x, -y, -z]),
        np.array([ x, -y, -z])
    ]
    edges = [
        # Top
        [0, 1, 2, 3, 0],
        # Bottom
        [4, 5, 6, 7, 4]
    ]
    edge_attributes = {
        (0, 1): {'resolution': resolutions[0]},
        (1, 2): {'resolution': resolutions[1]},
        (2, 3): {'resolution': resolutions[0]},
        (3, 0): {'resolution': resolutions[1]},
        (4, 5): {'resolution': resolutions[0]},
        (5, 6): {'resolution': resolutions[1]},
        (6, 7): {'resolution': resolutions[0]},
        (7, 4): {'resolution': resolutions[1]}
    }
    faces = [
        # Top
        [0, 1, 2, 3],
        # Bottom
        [7, 6, 5, 4]
    ]

    if band_size is not None:
        band_offset_xy = band_size * math.sqrt(0.5)
        band_offset_z = band_offset

        vertices.extend([
            np.array([ x + band_offset_xy,  y + band_offset_xy, band_offset_z]),
            np.array([-x - band_offset_xy,  y + band_offset_xy, band_offset_z]),
            np.array([-x - band_offset_xy, -y - band_offset_xy, band_offset_z]),
            np.array([ x + band_offset_xy, -y - band_offset_xy, band_offset_z])
        ])
        edges.extend([
            # Middle
            [8, 9, 10, 11, 8],
            # Sides, upper half
            [0, 8],
            [1, 9],
            [2, 10],
            [3, 11],
            # Sides, lower half
            [8, 4],
            [9, 5],
            [10, 6],
            [11, 7]
        ])
        edge_attributes.update({
            # Middle
            (8, 9): {'resolution': resolutions[0]},
            (9, 10): {'resolution': resolutions[1]},
            (10, 11): {'resolution': resolutions[0]},
            (11, 8): {'resolution': resolutions[1]},
            # Sides, upper half
            (0, 8): {'resolution': resolutions[2]},
            (1, 9): {'resolution': resolutions[2]},
            (2, 10): {'resolution': resolutions[2]},
            (3, 11): {'resolution': resolutions[2]},
            # Sides, lower half
            (8, 4): {'resolution': resolutions[2]},
            (9, 5): {'resolution': resolutions[2]},
            (10, 6): {'resolution': resolutions[2]},
            (11, 7): {'resolution': resolutions[2]}
        })
        faces.extend([
            # Sides, upper half
            [8, 9, 1, 0],
            [9, 10, 2, 1],
            [10, 11, 3, 2],
            [11, 8, 0, 3],
            # Sides, lower half
            [4, 5, 9, 8],
            [5, 6, 10, 9],
            [6, 7, 11, 10],
            [7, 4, 8, 11]
        ])
    else:
        edges.extend([
            # Sides
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7]
        ])
        edge_attributes.update({
            # Middle
            (0, 4): {'resolution': resolutions[2]},
            (1, 5): {'resolution': resolutions[2]},
            (2, 6): {'resolution': resolutions[2]},
            (3, 7): {'resolution': resolutions[2]}
        })
        faces.extend([
            # Sides
            [4, 5, 1, 0],
            [5, 6, 2, 1],
            [6, 7, 3, 2],
            [7, 4, 0, 3]
        ])

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=default_resolution,
        edge_attributes=edge_attributes
    )

    # Override top face generation
    if mark_radius is not None:
        element = body.find_face([0, 1, 2, 3])
        element.functor = top_face_functor

    body_patches = body.build()
    if mark_patches is not None:
        return (bezier.patch_to_mesh(body_patches), bezier.patch_to_mesh(mark_patches))
    return bezier.patch_to_mesh(body_patches)


def make_box_with_plinth(size, band_size, band_offset, cutout_length, cutout_height, chamfer,
                         edge_resolution, line_resolution):
    # pylint: disable=invalid-name
    x, y = np.array(size[0:2]) / 2.0
    z = size[2]
    # pylint: enable=invalid-name

    top_resolution = 2 # Fixed resolution for strip generation
    band_xy = np.array(size[0:2]) / 2.0 + band_size
    bottom_slope = band_size / band_offset if band_size > 0.0 else 1.0
    xy_offset = cutout_height * bottom_slope

    vertices = [
        # Offset 0
        np.array([ x,  y, z]),
        np.array([ x, -y, z]),
        np.array([-x, -y, z]),
        np.array([-x,  y, z]),

        # Offset 4
        np.array([ x + band_size,  y + band_size, band_offset]),
        np.array([ x + band_size, -y - band_size, band_offset]),
        np.array([-x - band_size, -y - band_size, band_offset]),
        np.array([-x - band_size,  y + band_size, band_offset]),

        # Offset 8
        np.array([ x - cutout_length,  y + xy_offset, cutout_height]),
        np.array([                 x,  y + xy_offset, cutout_height]),
        np.array([                 x, -y - xy_offset, cutout_height]),
        np.array([ x - cutout_length, -y - xy_offset, cutout_height]),
        np.array([-x + cutout_length, -y - xy_offset, cutout_height]),
        np.array([                -x, -y - xy_offset, cutout_height]),
        np.array([                -x,  y + xy_offset, cutout_height]),
        np.array([-x + cutout_length,  y + xy_offset, cutout_height]),

        # Offset 16
        np.array([ x - cutout_length,  y, 0.0]),
        np.array([ x - cutout_length, -y, 0.0]),
        np.array([-x + cutout_length, -y, 0.0]),
        np.array([-x + cutout_length,  y, 0.0])
    ]
    vertex_attributes = {
    }
    edges = [
        # Top
        [0, 1, 2, 3, 0],
        # Medium
        [4, 5, 6, 7, 4],
        [8, 9, 10, 11, 12, 13, 14, 15, 8],
        [8, 11], [12, 15],
        # Bottom
        [16, 17, 18, 19, 16],
        # Sides
        [0, 4], [1, 5], [2, 6], [3, 7],
        [4, 8], [4, 9], [5, 10], [5, 11], [6, 12], [6, 13], [7, 14], [7, 15],
        [8, 16], [11, 17], [12, 18], [15, 19]
    ]
    edge_attributes = {
        ( 8, 11): {'inversion': True},
        (12, 15): {'inversion': True},

        ( 0,  3): {'resolution': top_resolution},
        ( 1,  2): {'resolution': top_resolution},
        ( 4,  7): {'resolution': top_resolution},
        ( 5,  6): {'resolution': top_resolution},
        ( 8, 15): {'resolution': top_resolution},
        (11, 12): {'resolution': top_resolution},
        (16, 19): {'resolution': top_resolution},
        (17, 18): {'resolution': top_resolution}
    }
    faces = [
        # Top
        [3, 2, 1, 0],
        # Medium
        [8, 9, 10, 11], [12, 13, 14, 15],
        # Bottom
        [16, 17, 18, 19],
        # Sides
        [5, 4, 0, 1], [6, 5, 1, 2], [7, 6, 2, 3], [4, 7, 3, 0],
        [9, 8, 4], [11, 10, 5], [13, 12, 6], [15, 14, 7],
        [4, 5, 10, 9], [5, 6, 12, 11], [6, 7, 14, 13], [7, 4, 8, 15],
        # Bottom sides
        [8, 11, 17, 16], [12, 15, 19, 18],
        [16, 19, 15, 8], [18, 17, 11, 12]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes,
        edge_attributes=edge_attributes
    )
    return bezier.patch_to_mesh(body.build())


def make_chip_body(size, chamfer, edge_resolution):
    x_half = size[0] / 2.0
    y, z = size[1], size[2] # pylint: disable=invalid-name

    shape = make_rounded_rect(size=np.array([z, y]), roundness=chamfer, segments=edge_resolution)
    shape_points = []
    for element in shape:
        shape_points.extend(element.tessellate())
    shape_points = curves.optimize(shape_points)

    path_points = [np.array([x_half, 0.0, 0.0]), np.array([-x_half, 0.0, 0.0])]
    slices = curves.loft(path=path_points, shape=shape_points)
    return geometry.build_loft_mesh(slices, False, False)


def make_chip_lead_cap(size, chamfer, inversion, edge_resolution, line_resolution, axis):
    x, y, z = np.array(size) / 2.0 # pylint: disable=invalid-name

    vertices = [
        # Offset 0
        np.array([ x,  y, -z]),
        np.array([-x,  y, -z]),
        np.array([-x, -y, -z]),
        np.array([ x, -y, -z]),

        # Offset 4
        np.array([ x,  y, z]),
        np.array([-x,  y, z]),
        np.array([-x, -y, z]),
        np.array([ x, -y, z])
    ]

    edges = []
    faces = []

    if axis == 0:
        edges.extend([[1, 0], [2, 3], [5, 4], [6, 7]])
        if inversion:
            edges.append([1, 2, 6, 5, 1])
            faces.append([1, 2, 6, 5])
        else:
            edges.append([3, 0, 4, 7, 3])
            faces.append([3, 0, 4, 7])
    elif axis == 1:
        edges.extend([[2, 1], [3, 0], [6, 5], [7, 4]])
        if inversion:
            edges.append([2, 3, 7, 6, 2])
            faces.append([2, 3, 7, 6])
        else:
            edges.append([0, 1, 5, 4, 0])
            faces.append([0, 1, 5, 4])
    else:
        edges.extend([[0, 4], [1, 5], [2, 6], [3, 7]])
        if inversion:
            edges.append([0, 1, 2, 3, 0])
            faces.append([0, 1, 2, 3])
        else:
            edges.append([4, 5, 6, 7, 4])
            faces.append([4, 5, 6, 7])

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )
    return bezier.patch_to_mesh(body.build())


def make_chip_lead_slope(case_size, lead_size, case_chamfer, lead_chamfer, inversion,
                         edge_resolution, line_resolution):
    roundness = lead_chamfer
    x_lead_half = lead_size[0] / 2.0
    y_case, z_case = case_size[1], case_size[2]
    y_lead, z_lead = lead_size[1], lead_size[2]

    if inversion:
        p0 = np.array([-x_lead_half + roundness, 0.0, 0.0])
        p1 = np.array([x_lead_half - roundness, 0.0, 0.0])
        p2 = np.array([x_lead_half, 0.0, 0.0])
    else:
        p0 = np.array([x_lead_half - roundness, 0.0, 0.0])
        p1 = np.array([-x_lead_half + roundness, 0.0, 0.0])
        p2 = np.array([-x_lead_half, 0.0, 0.0])

    path = []
    path.append(curves.Line(p0, p1, line_resolution))
    path.append(curves.Bezier(p1, (p2 - p1) / 3.0, p2, (p1 - p2) / 3.0, edge_resolution))

    path_points = []
    for element in path:
        path_points.extend(element.tessellate())
    path_points = curves.optimize(path_points)

    case_shape = make_rounded_rect(size=np.array([z_case, y_case]),
                                   roundness=case_chamfer, segments=edge_resolution)
    case_points = []
    for element in case_shape:
        case_points.extend(element.tessellate())
    case_points = curves.optimize(case_points)

    lead_shape = make_rounded_rect(size=np.array([z_lead, y_lead]),
                                   roundness=roundness, segments=edge_resolution)
    lead_points = []
    for element in lead_shape:
        lead_points.extend(element.tessellate())
    lead_points = curves.optimize(lead_points)

    def mesh_morphing_func(number):
        if number >= line_resolution:
            number = edge_resolution - (number - line_resolution)
            t_pos = math.sin((math.pi / 2.0) * (number / edge_resolution))
            points = []
            for i, point in enumerate(case_points):
                points.append(point + (lead_points[i] - point) * t_pos)
            return points
        return lead_points

    slices = curves.loft(path=path_points, shape=None, morphing=mesh_morphing_func)
    return geometry.build_loft_mesh(slices, False, False)


def make_chip_leads(case_size, lead_size, case_chamfer, lead_chamfer, edge_resolution,
                    line_resolution):
    mesh_a = make_chip_lead_cap(size=lead_size, chamfer=lead_chamfer, inversion=False,
                                edge_resolution=edge_resolution, line_resolution=line_resolution,
                                axis=0)
    mesh_a.translate(np.array([(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))
    slope_a = make_chip_lead_slope(case_size=case_size, lead_size=lead_size,
                                   case_chamfer=case_chamfer, lead_chamfer=lead_chamfer,
                                   inversion=False, edge_resolution=edge_resolution,
                                   line_resolution=line_resolution)
    slope_a.translate(np.array([(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))

    mesh_b = make_chip_lead_cap(size=lead_size, chamfer=lead_chamfer, inversion=True,
                                edge_resolution=edge_resolution, line_resolution=line_resolution,
                                axis=0)
    mesh_b.translate(np.array([-(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))
    slope_b = make_chip_lead_slope(case_size=case_size, lead_size=lead_size,
                                   case_chamfer=case_chamfer, lead_chamfer=lead_chamfer,
                                   inversion=True, edge_resolution=edge_resolution,
                                   line_resolution=line_resolution)
    slope_b.translate(np.array([-(case_size[0] + lead_size[0]) / 2.0, 0.0, 0.0]))

    mesh = model.Mesh()
    mesh.append(mesh_a)
    mesh.append(mesh_b)
    mesh.append(slope_a)
    mesh.append(slope_b)
    mesh.optimize()
    return mesh


def make_chip(body_size, lead_size, body_chamfer, lead_chamfer,
              chamfer_resolution, edge_resolution, line_resolution):
    lead = make_chip_leads(
        case_size=body_size,
        lead_size=lead_size,
        case_chamfer=body_chamfer,
        lead_chamfer=lead_chamfer,
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )
    body = make_chip_body(
        size=body_size,
        chamfer=body_chamfer,
        edge_resolution=edge_resolution
    )
    return (body, lead)

def make_chip_shunt(length, width, thickness, clearance, lead_length, active_width, chamfer,
                    edge_resolution, line_resolution, slope_resolution):
    slope = np.deg2rad(30.0)
    slope_length = clearance / math.sin(slope)
    weight = curves.calc_bezier_weight(angle=slope * 2.0)
    slope_tension = np.array([slope_length, 0.0, 0.0]) * weight

    y_lead = width / 2.0
    y_body = active_width / 2.0 # Unused
    x_lead_start = length / 2.0
    z_lead_start = thickness / 2.0
    x_slope_start = length / 2.0 - lead_length
    z_slope_start = thickness / 2.0
    x_slope_end = length / 2.0 - lead_length - slope_length
    z_slope_end = thickness / 2.0 + clearance
    x_body = length / 2.0 - lead_length - slope_length - thickness
    z_body = thickness / 2.0 + clearance

    def make_vertex_group(x, y, z, t): # pylint: disable=invalid-name
        return [
            np.array([ x,  y, z + t]),
            np.array([ x,  y, z - t]),
            np.array([ x, -y, z - t]),
            np.array([ x, -y, z + t])
        ]

    vertices = \
        make_vertex_group(x_lead_start, y_lead, z_lead_start, thickness / 2.0) + \
        make_vertex_group(x_slope_start, y_lead, z_slope_start, thickness / 2.0) + \
        make_vertex_group(x_slope_end, y_lead, z_slope_end, thickness / 2.0) + \
        make_vertex_group(x_body, y_lead, z_body, thickness / 2.0) + \
        make_vertex_group(-x_body, y_lead, z_body, thickness / 2.0) + \
        make_vertex_group(-x_slope_end, y_lead, z_slope_end, thickness / 2.0) + \
        make_vertex_group(-x_slope_start, y_lead, z_slope_start, thickness / 2.0) + \
        make_vertex_group(-x_lead_start, y_lead, z_lead_start, thickness / 2.0)

    body_vertex_attributes = {}
    for i in list(range(3)) + list(range(5, 8)):
        for j in range(4):
            body_vertex_attributes[i * 4 + j] = {'discard': True}

    lead_vertex_attributes = {}
    for i in range(4):
        lead_vertex_attributes[4 + i] = {'bezier': {8 + i: -slope_tension}}
        lead_vertex_attributes[8 + i] = {'bezier': {4 + i: slope_tension}}
        lead_vertex_attributes[20 + i] = {'bezier': {24 + i: -slope_tension}}
        lead_vertex_attributes[24 + i] = {'bezier': {20 + i: slope_tension}}

    edges = []
    for i in range(len(vertices) // 4):
        edges.extend(bezier.unpack_edges([list(range(i * 4, (i + 1) * 4)) + [i * 4]]))
        if i > 0:
            edges.extend([[(i - 1) * 4 + j, i * 4 + j] for j in range(4)])

    edge_attributes = {
        (4 + i, 8 + i): {'resolution': slope_resolution} for i in range(4)
    } | {
        (20 + i, 24 + i): {'resolution': slope_resolution} for i in range(4)
    }
    lead_edge_attributes = edge_attributes | {
        (12 + i, 16 + i): {'hidden': True} for i in range(4)
    }

    lead_faces = [[3, 2, 1, 0], [28, 29, 30, 31]]
    body_faces = []
    for i in range(len(vertices) // 4 - 1):
        section = [
            [i * 4 + 0, i * 4 + 1, (i + 1) * 4 + 1, (i + 1) * 4 + 0],
            [i * 4 + 1, i * 4 + 2, (i + 1) * 4 + 2, (i + 1) * 4 + 1],
            [i * 4 + 2, i * 4 + 3, (i + 1) * 4 + 3, (i + 1) * 4 + 2],
            [i * 4 + 3, i * 4 + 0, (i + 1) * 4 + 0, (i + 1) * 4 + 3]
        ]
        if i == 3:
            body_faces.extend(section)
        else:
            lead_faces.extend(section)

    body_object = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=body_faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=body_vertex_attributes,
        edge_attributes=edge_attributes
    )
    lead_object = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=lead_faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=lead_vertex_attributes,
        edge_attributes=lead_edge_attributes
    )
    return (bezier.patch_to_mesh(body_object.build()), bezier.patch_to_mesh(lead_object.build()))


def make_carved_box(size, niche_size, chamfer, roundness, edge_resolution, line_resolution):
    # pylint: disable=invalid-name
    x, y, z = np.array(size) / 2.0
    r = roundness
    # pylint: enable=invalid-name

    niche_depth = niche_size[0]
    niche_width_half = niche_size[1] / 2.0
    niche_height = niche_size[2]

    vertices = [
        # Offset 0
        np.array([ x,  y, z]),
        np.array([ x, -y, z]),
        np.array([-x, -y, z]),
        np.array([-x,  y, z]),

        # Offset 4
        np.array([               x,  niche_width_half, -z + niche_height]),
        np.array([ x - niche_depth,  niche_width_half, -z + niche_height]),
        np.array([ x - niche_depth, -niche_width_half, -z + niche_height]),
        np.array([               x, -niche_width_half, -z + niche_height]),
        # Offset 8
        np.array([              -x, -niche_width_half, -z + niche_height]),
        np.array([-x + niche_depth, -niche_width_half, -z + niche_height]),
        np.array([-x + niche_depth,  niche_width_half, -z + niche_height]),
        np.array([              -x,  niche_width_half, -z + niche_height]),

        # Offset 12
        np.array([               x,                 y, -z]),
        np.array([               x,  niche_width_half, -z]),
        np.array([ x - niche_depth,  niche_width_half, -z]),
        np.array([ x - niche_depth, -niche_width_half, -z]),
        # Offset 16
        np.array([               x, -niche_width_half, -z]),
        np.array([               x,                -y, -z]),
        np.array([              -x,                -y, -z]),
        np.array([              -x, -niche_width_half, -z]),
        # Offset 20
        np.array([-x + niche_depth, -niche_width_half, -z]),
        np.array([-x + niche_depth,  niche_width_half, -z]),
        np.array([              -x,  niche_width_half, -z]),
        np.array([              -x,                 y, -z])
    ]
    vertex_attributes = {
        0:  {'chamfer': { 1: r,  3: r}},
        1:  {'chamfer': { 2: r,  0: r}},
        2:  {'chamfer': { 3: r,  1: r}},
        3:  {'chamfer': { 0: r,  2: r}},
        12: {'chamfer': {13: r, 23: r}},
        17: {'chamfer': {18: r, 16: r}},
        18: {'chamfer': {19: r, 17: r}},
        23: {'chamfer': {12: r, 22: r}},

        5:  {'inversion': True},
        6:  {'inversion': True},
        9:  {'inversion': True},
        10: {'inversion': True}
    }
    edges = [
        # Top
        [0, 1, 2, 3, 0],
        # Medium
        [4, 5, 6, 7, 4], [8, 9, 10, 11, 8],
        # Bottom
        [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 12],
        [12, 14], [15, 17], [18, 20], [21, 23],
        [14, 21], [15, 20],
        # Top sides
        [0, 4], [0, 12], [1, 7], [1, 17],
        [2, 8], [2, 18], [3, 11], [3, 23],
        # Bottom sides
        [4, 13], [5, 14], [6, 15], [7, 16],
        [8, 19], [9, 20], [10, 21], [11, 22]
    ]
    edge_attributes = {
        ( 4,  5): {'inversion': True},
        ( 5,  6): {'inversion': True},
        ( 6,  7): {'inversion': True},
        ( 8,  9): {'inversion': True},
        ( 9, 10): {'inversion': True},
        (10, 11): {'inversion': True},
        ( 5, 14): {'inversion': True},
        ( 6, 15): {'inversion': True},
        ( 9, 20): {'inversion': True},
        (10, 21): {'inversion': True}
    }
    faces = [
        # Top
        [3, 2, 1, 0],
        # Bottom
        [14, 15, 20, 21],
        [12, 13, 14], [12, 14, 21, 23], [21, 22, 23],
        [15, 16, 17], [15, 17, 18, 20], [18, 19, 20],
        # Sides
        [1, 2, 18, 17], [3, 0, 12, 23],
        [4, 13, 12, 0], [1, 17, 16, 7], [0, 1, 7, 4],
        [3, 23, 22, 11], [8, 19, 18, 2], [11, 8, 2, 3],
        # Niches
        [7, 6, 5, 4],
        [4, 5, 14, 13], [16, 15, 6, 7], [5, 6, 15, 14],
        [11, 10, 9, 8],
        [21, 20, 9, 10], [8, 9, 20, 19], [10, 11, 22, 21]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes,
        edge_attributes=edge_attributes
    )
    return bezier.patch_to_mesh(body.build())


def make_rounded_box(size, roundness, chamfer, edge_resolution, line_resolution,
                     plane_resolution=None, band_size=None, band_offset=0.0,
                     mark_radius=None, mark_offset=np.zeros(3), mark_resolution=24):
    if band_size is None:
        raise ValueError() # TODO
    if plane_resolution is None:
        plane_resolution = line_resolution

    # pylint: disable=invalid-name
    x, y, z = np.array(size) / 2.0
    r = roundness * math.sqrt(0.5)
    # pylint: enable=invalid-name

    band_offset_xy = band_size * math.sqrt(0.5)
    band_offset_z = band_offset
    mark_patches = None

    def top_face_functor(points, controls, resolution, inversion):
        nonlocal mark_patches

        patches = make_hollow_plane(
            points=points,
            controls=controls,
            hollow_offset=mark_offset,
            hollow_radius=mark_radius,
            circle_resolution=mark_resolution,
            plane_resolution=plane_resolution,
            side_resolutions=resolution,
            inversion=inversion
        )
        mark_patches = patches[1]
        return patches[0]

    vertices = [
        # Offset 0
        np.array([     x,  y - r, z]),
        np.array([ x - r,      y, z]),
        np.array([-x + r,      y, z]),
        np.array([    -x,  y - r, z]),
        np.array([    -x, -y + r, z]),
        np.array([-x + r,     -y, z]),
        np.array([ x - r,     -y, z]),
        np.array([     x, -y + r, z]),

        # Offset 8
        np.array([     x + band_offset_xy,  y - r + band_offset_xy, band_offset_z]),
        np.array([ x - r + band_offset_xy,      y + band_offset_xy, band_offset_z]),
        np.array([-x + r - band_offset_xy,      y + band_offset_xy, band_offset_z]),
        np.array([    -x - band_offset_xy,  y - r + band_offset_xy, band_offset_z]),
        np.array([    -x - band_offset_xy, -y + r - band_offset_xy, band_offset_z]),
        np.array([-x + r - band_offset_xy,     -y - band_offset_xy, band_offset_z]),
        np.array([ x - r + band_offset_xy,     -y - band_offset_xy, band_offset_z]),
        np.array([     x + band_offset_xy, -y + r - band_offset_xy, band_offset_z]),

        # Offset 16
        np.array([     x,  y - r, -z]),
        np.array([ x - r,      y, -z]),
        np.array([-x + r,      y, -z]),
        np.array([    -x,  y - r, -z]),
        np.array([    -x, -y + r, -z]),
        np.array([-x + r,     -y, -z]),
        np.array([ x - r,     -y, -z]),
        np.array([     x, -y + r, -z])
    ]
    edges = [
        # Top
        [0, 1, 2, 3, 4, 5, 6, 7, 0],
        [0, 3], [4, 7],
        # Middle
        [8, 9, 10, 11, 12, 13, 14, 15, 8],
        # Bottom
        [16, 17, 18, 19, 20, 21, 22, 23, 16],
        [16, 19], [20, 23],
        # Sides, upper half
        [0, 8], [1, 9], [2, 10], [3, 11], [4, 12], [5, 13], [6, 14], [7, 15],
        # Sides, lower half
        [8, 16], [9, 17], [10, 18], [11, 19], [12, 20], [13, 21], [14, 22], [15, 23]
    ]
    faces = [
        # Top
        [0, 1, 2, 3],
        [0, 3, 4, 7],
        [7, 4, 5, 6],
        # Bottom
        [19, 18, 17, 16],
        [23, 20, 19, 16],
        [22, 21, 20, 23],
        # Sides, upper half
        [8, 9, 1, 0],
        [9, 10, 2, 1],
        [10, 11, 3, 2],
        [11, 12, 4, 3],
        [12, 13, 5, 4],
        [13, 14, 6, 5],
        [14, 15, 7, 6],
        [15, 8, 0, 7],
        # Sides, lower half
        [16, 17, 9, 8],
        [17, 18, 10, 9],
        [18, 19, 11, 10],
        [19, 20, 12, 11],
        [20, 21, 13, 12],
        [21, 22, 14, 13],
        [22, 23, 15, 14],
        [23, 16, 8, 15]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )

    # Override top face generation
    if mark_radius is not None:
        element = body.find_face([0, 3, 4, 7])
        element.functor = top_face_functor

    body_patches = body.build()
    if mark_patches is not None:
        return (bezier.patch_to_mesh(body_patches), bezier.patch_to_mesh(mark_patches))
    return bezier.patch_to_mesh(body_patches)


def make_sloped_box(size, chamfer, slope, slope_height, edge_resolution, line_resolution,
                    band_size=None, band_offset=0.0):
    if band_size is None:
        raise ValueError() # TODO

    x, y, z = np.array(size) / 2.0 # pylint: disable=invalid-name
    z_mean = z - slope_height
    y_slope = y - slope_height / math.tan(slope)

    band_offset_xy = band_size * math.sqrt(0.5)
    band_offset_z = band_offset
    offset = band_offset_xy - z_mean * (band_offset_xy / z)
    x_mean = x + offset
    y_mean = y + offset

    vertices = [
        # Offset 0
        np.array([ x,  y, -z]),
        np.array([-x,  y, -z]),
        np.array([-x, -y, -z]),
        np.array([ x, -y, -z]),

        # Offset 4
        np.array([ x + band_offset_xy,  y + band_offset_xy, band_offset_z]),
        np.array([-x - band_offset_xy,  y + band_offset_xy, band_offset_z]),
        np.array([-x - band_offset_xy, -y - band_offset_xy, band_offset_z]),
        np.array([ x + band_offset_xy, -y - band_offset_xy, band_offset_z]),

        # Offset 8
        np.array([ x_mean, y_mean, z_mean]),
        np.array([-x_mean, y_mean, z_mean]),

        # Offset 10
        np.array([ x, y_slope, z]),
        np.array([-x, y_slope, z]),
        np.array([-x, -y, z]),
        np.array([ x, -y, z])
    ]
    edges = [
        [0, 1, 2, 3, 0],
        [4, 5, 6, 7, 4],
        [8, 9],
        [10, 11, 12, 13, 10],
        [2, 6, 12], [3, 7, 13],
        [1, 5, 9, 11], [0, 4, 8, 10],
        [9, 12], [8, 13]
    ]
    faces = [
        [3, 2, 1, 0],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
        [4, 5, 9, 8],
        [8, 9, 11, 10],
        [6, 7, 13, 12],
        [10, 11, 12, 13],
        [9, 12, 11], [10, 13, 8],
        [5, 6, 12, 9], [8, 13, 7, 4]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution
    )
    return bezier.patch_to_mesh(body.build())


def make_rounded_rect(size, roundness, segments, segments_line=1):
    # pylint: disable=invalid-name
    dx, dy = size[0] / 2.0, size[1] / 2.0
    r, rb = roundness, roundness * curves.calc_bezier_weight(angle=math.pi / 2.0)
    # pylint: enable=invalid-name

    shape = []
    shape.append(curves.Line((-dx + r, dy, 0.0), (dx - r, dy, 0.0), segments_line))
    shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                               (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
    shape.append(curves.Line((dx, dy - r, 0.0), (dx, -dy + r, 0.0), segments_line))
    shape.append(curves.Bezier((dx, -dy + r, 0.0), (0.0, -rb, 0.0),
                               (dx - r, -dy, 0.0), (rb, 0.0, 0.0), segments))
    shape.append(curves.Line((dx - r, -dy, 0.0), (-dx + r, -dy, 0.0), segments_line))
    shape.append(curves.Bezier((-dx + r, -dy, 0.0), (-rb, 0.0, 0.0),
                               (-dx, -dy + r, 0.0), (0.0, -rb, 0.0), segments))
    shape.append(curves.Line((-dx, -dy + r, 0.0), (-dx, dy - r, 0.0), segments_line))
    shape.append(curves.Bezier((-dx, dy - r, 0.0), (0.0, rb, 0.0),
                               (-dx + r, dy, 0.0), (-rb, 0.0, 0.0), segments))
    return shape


def make_rounded_rect_half(size, rotate, roundness, segments):
    # pylint: disable=invalid-name
    dx, dy = size[0], size[1]
    r, rb = roundness, roundness * curves.calc_bezier_weight(angle=math.pi / 2.0)
    # pylint: enable=invalid-name

    shape = []
    if not rotate:
        dy /= 2.0
        shape.append(curves.Line((0.0, dy, 0.0), (dx - r, dy, 0.0), 1))
        shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                                   (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
        shape.append(curves.Line((dx, dy - r, 0.0), (dx, -dy + r, 0.0), 1))
        shape.append(curves.Bezier((dx, -dy + r, 0.0), (0.0, -rb, 0.0),
                                   (dx - r, -dy, 0.0), (rb, 0.0, 0.0), segments))
        shape.append(curves.Line((dx - r, -dy, 0.0), (0.0, -dy, 0.0), 1))
    else:
        dx /= 2.0
        shape.append(curves.Line((-dx, 0.0, 0.0), (-dx, dy - r, 0.0), 1))
        shape.append(curves.Bezier((-dx, dy - r, 0.0), (0.0, rb, 0.0),
                                   (-dx + r, dy, 0.0), (-rb, 0.0, 0.0), segments))
        shape.append(curves.Line((-dx + r, dy, 0.0), (dx - r, dy, 0.0), 1))
        shape.append(curves.Bezier((dx - r, dy, 0.0), (rb, 0.0, 0.0),
                                   (dx, dy - r, 0.0), (0.0, rb, 0.0), segments))
        shape.append(curves.Line((dx, dy - r, 0.0), (dx, 0.0, 0.0), 1))
    return shape


def make_bent_fork_pin_mesh(width, height, length, thickness, top_roundness, bottom_roundness,
                            cutout_width, cutout_height, end_slope, chamfer,
                            edge_resolution, line_resolution, slope_resolution):
    if chamfer * 2.0 >= thickness:
        raise ValueError()

    if isinstance(bottom_roundness, float):
        r_bot = np.array([bottom_roundness, bottom_roundness])
    else:
        r_bot = np.array(bottom_roundness)
    if isinstance(top_roundness, float):
        r_top = np.array([top_roundness, top_roundness])
    else:
        r_top = np.array(top_roundness)
    if any(r_bot <= thickness) or any(r_top <= thickness):
        raise ValueError()

    # pylint: disable=invalid-name
    t = thickness
    x = length + r_top[0]
    y = width / 2.0
    z = height
    # pylint: enable=invalid-name

    weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
    end_offset = t * np.array([math.sin(end_slope), math.cos(end_slope)])

    vertices = [
        # Offset 0
        np.array([0.0,  y,   t]),
        np.array([0.0,  y, 0.0]),
        np.array([0.0, -y, 0.0]),
        np.array([0.0, -y,   t]),

        # Offset 4
        np.array([x - r_bot[0],  y,   t]),
        np.array([x - r_bot[0],  y, 0.0]),
        np.array([x - r_bot[0], -y, 0.0]),
        np.array([x - r_bot[0], -y,   t]),

        # Offset 8
        np.array([x - t,  y, r_bot[1]]),
        np.array([    x,  y, r_bot[1]]),
        np.array([    x, -y, r_bot[1]]),
        np.array([x - t, -y, r_bot[1]]),

        # Offset 12
        np.array([x - t,  cutout_width / 2.0, z - cutout_height]),
        np.array([    x,  cutout_width / 2.0, z - cutout_height]),
        np.array([    x, -cutout_width / 2.0, z - cutout_height]),
        np.array([x - t, -cutout_width / 2.0, z - cutout_height]),

        # Offset 16
        np.array([x - t,  cutout_width / 2.0, z - r_top[1]]),
        np.array([x - t,                   y, z - r_top[1]]),
        np.array([    x,                   y, z - r_top[1]]),
        np.array([    x,  cutout_width / 2.0, z - r_top[1]]),
        np.array([    x, -cutout_width / 2.0, z - r_top[1]]),
        np.array([    x,                  -y, z - r_top[1]]),
        np.array([x - t,                  -y, z - r_top[1]]),
        np.array([x - t, -cutout_width / 2.0, z - r_top[1]]),

        # Offset 24
        np.array([x - r_top[0] - end_offset[0],  cutout_width / 2.0, z - end_offset[1]]),
        np.array([x - r_top[0] - end_offset[0],                   y, z - end_offset[1]]),
        np.array([                x - r_top[0],                   y,                 z]),
        np.array([                x - r_top[0],  cutout_width / 2.0,                 z]),
        np.array([                x - r_top[0], -cutout_width / 2.0,                 z]),
        np.array([                x - r_top[0],                  -y,                 z]),
        np.array([x - r_top[0] - end_offset[0],                  -y, z - end_offset[1]]),
        np.array([x - r_top[0] - end_offset[0], -cutout_width / 2.0, z - end_offset[1]]),

        # Offset 32
        np.array([0.0,  cutout_width / 2.0, z - t]),
        np.array([0.0,                   y, z - t]),
        np.array([0.0,                   y,     z]),
        np.array([0.0,  cutout_width / 2.0,     z]),
        np.array([0.0, -cutout_width / 2.0,     z]),
        np.array([0.0,                  -y,     z]),
        np.array([0.0,                  -y, z - t]),
        np.array([0.0, -cutout_width / 2.0, z - t])
    ]
    vertex_attributes = {
        # Bottom Bezier corner
        4:  {'bezier': { 8: np.array([(r_bot[0] - t) * weight, 0.0, 0.0])}},
        5:  {'bezier': { 9: np.array([      r_bot[0] * weight, 0.0, 0.0])}},
        6:  {'bezier': {10: np.array([      r_bot[0] * weight, 0.0, 0.0])}},
        7:  {'bezier': {11: np.array([(r_bot[0] - t) * weight, 0.0, 0.0])}},
        8:  {'bezier': { 4: np.array([0.0, 0.0, -(r_bot[1] - t) * weight])}},
        9:  {'bezier': { 5: np.array([0.0, 0.0,       -r_bot[1] * weight])}},
        10: {'bezier': { 6: np.array([0.0, 0.0,       -r_bot[1] * weight])}},
        11: {'bezier': { 7: np.array([0.0, 0.0, -(r_bot[1] - t) * weight])}},

        # Top right Bezier corner
        16: {'bezier': {24: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        17: {'bezier': {25: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        18: {'bezier': {26: np.array([0.0, 0.0,       r_top[1] * weight])}},
        19: {'bezier': {27: np.array([0.0, 0.0,       r_top[1] * weight])}},
        24: {'bezier': {16: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},
        25: {'bezier': {17: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},
        26: {'bezier': {18: np.array([      r_top[0] * weight, 0.0, 0.0])}},
        27: {'bezier': {19: np.array([      r_top[0] * weight, 0.0, 0.0])}},

        # # Top left Bezier corner
        20: {'bezier': {28: np.array([0.0, 0.0,       r_top[1] * weight])}},
        21: {'bezier': {29: np.array([0.0, 0.0,       r_top[1] * weight])}},
        22: {'bezier': {30: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        23: {'bezier': {31: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        28: {'bezier': {20: np.array([      r_top[0] * weight, 0.0, 0.0])}},
        29: {'bezier': {21: np.array([      r_top[0] * weight, 0.0, 0.0])}},
        30: {'bezier': {22: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},
        31: {'bezier': {23: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},

        # Unconnected end
        32: {'discard': True},
        33: {'discard': True},
        34: {'discard': True},
        35: {'discard': True},
        36: {'discard': True},
        37: {'discard': True},
        38: {'discard': True},
        39: {'discard': True}
    }
    edges = [
        # Bottom
        [0, 1, 2, 3, 0],
        [4, 5, 6, 7, 4],
        # Medium
        [8, 9, 10, 11, 8],
        [12, 13, 14, 15, 12],
        # Top
        [16, 17, 18, 19, 16], [20, 21, 22, 23, 20],
        [24, 25, 26, 27, 24], [28, 29, 30, 31, 28],
        # Bottom sides
        [0, 4], [1, 5], [2, 6], [3, 7],
        # Corner sides
        [4, 8], [5, 9], [6, 10], [7, 11],
        # Medium sides
        [8, 12], [8, 17], [9, 18], [9, 13], [10, 14], [10, 21], [11, 22], [11, 15],
        # Top sides
        [12, 16], [13, 19], [14, 20], [15, 23],
        [16, 24], [17, 25], [18, 26], [19, 27], [20, 28], [21, 29], [22, 30], [23, 31],
        # Unconnected ends
        [32, 33, 34, 35, 32], [36, 37, 38, 39, 36],
        [24, 32], [25, 33], [26, 34], [27, 35], [28, 36], [29, 37], [30, 38], [31, 39]
    ]
    edge_attributes = {
        # Bottom corner
        (4, 8):  {'resolution': slope_resolution},
        (5, 9):  {'resolution': slope_resolution},
        (6, 10): {'resolution': slope_resolution},
        (7, 11): {'resolution': slope_resolution},

        # Bottom part of cutout
        (12, 13): {'inversion': True},
        (14, 15): {'inversion': True},

        # Top right corner
        (16, 24): {'resolution': edge_resolution},
        (17, 25): {'resolution': edge_resolution},
        (18, 26): {'resolution': edge_resolution},
        (19, 27): {'resolution': edge_resolution},

        # Top left corner
        (20, 28): {'resolution': edge_resolution},
        (21, 29): {'resolution': edge_resolution},
        (22, 30): {'resolution': edge_resolution},
        (23, 31): {'resolution': edge_resolution}
    }
    faces = [
        # Bottom side
        [0, 1, 2, 3],
        # Bottom
        [4, 5, 1, 0], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3],
        # Bottom corner
        [8, 9, 5, 4], [9, 10, 6, 5], [10, 11, 7, 6], [11, 8, 4, 7],
        # Medium
        [15, 14, 13, 12],
        # Bottom to top transition - front and rear
        [12, 16, 17, 8], [11, 22, 23, 15], [8, 11, 15, 12],
        [9, 18, 19, 13], [14, 20, 21, 10], [13, 14, 10, 9],
        # Bottom to top transition - sides
        [12, 13, 19, 16], [14, 15, 23, 20],
        [17, 18, 9, 8], [21, 22, 11, 10],
        # Top corners
        [24, 25, 17, 16], [25, 26, 18, 17], [26, 27, 19, 18], [27, 24, 16, 19],
        [28, 29, 21, 20], [29, 30, 22, 21], [30, 31, 23, 22], [31, 28, 20, 23]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes,
        edge_attributes=edge_attributes
    )
    return bezier.patch_to_mesh(body.build())


def make_bent_pin_mesh(width, height, length, thickness, top_roundness, bottom_roundness,
                       end_slope, chamfer, edge_resolution, line_resolution, slope_resolution):
    if chamfer * 2.0 >= thickness:
        raise ValueError()

    if isinstance(bottom_roundness, float):
        r_bot = np.array([bottom_roundness, bottom_roundness])
    else:
        r_bot = np.array(list(bottom_roundness))
    if isinstance(top_roundness, float):
        r_top = np.array([top_roundness, top_roundness])
    else:
        r_top = np.array(list(top_roundness))
    if any(r_bot <= thickness) or any(r_top <= thickness):
        raise ValueError()

    # pylint: disable=invalid-name
    t = thickness
    x = length + r_top[0]
    y = width / 2.0
    z = height
    # pylint: enable=invalid-name

    weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
    end_offset = t * np.array([math.sin(end_slope), math.cos(end_slope)])

    vertices = [
        # Offset 0
        np.array([0.0,  y,   t]),
        np.array([0.0,  y, 0.0]),
        np.array([0.0, -y, 0.0]),
        np.array([0.0, -y,   t]),

        # Offset 4
        np.array([x - r_bot[0],  y,   t]),
        np.array([x - r_bot[0],  y, 0.0]),
        np.array([x - r_bot[0], -y, 0.0]),
        np.array([x - r_bot[0], -y,   t]),

        # Offset 8
        np.array([x - t,  y, r_bot[1]]),
        np.array([    x,  y, r_bot[1]]),
        np.array([    x, -y, r_bot[1]]),
        np.array([x - t, -y, r_bot[1]]),

        # Offset 12
        np.array([x - t,  y, z - r_top[1]]),
        np.array([    x,  y, z - r_top[1]]),
        np.array([    x, -y, z - r_top[1]]),
        np.array([x - t, -y, z - r_top[1]]),

        # Offset 16
        np.array([x - r_top[0] - end_offset[0],  y, z - end_offset[1]]),
        np.array([                x - r_top[0],  y,                 z]),
        np.array([                x - r_top[0], -y,                 z]),
        np.array([x - r_top[0] - end_offset[0], -y, z - end_offset[1]]),

        # Offset 20
        np.array([0.0,  y, z - t]),
        np.array([0.0,  y,     z]),
        np.array([0.0, -y,     z]),
        np.array([0.0, -y, z - t])
    ]
    vertex_attributes = {
        # Bottom Bezier corner
        4:  {'bezier': { 8: np.array([(r_bot[0] - t) * weight, 0.0, 0.0])}},
        5:  {'bezier': { 9: np.array([      r_bot[0] * weight, 0.0, 0.0])}},
        6:  {'bezier': {10: np.array([      r_bot[0] * weight, 0.0, 0.0])}},
        7:  {'bezier': {11: np.array([(r_bot[0] - t) * weight, 0.0, 0.0])}},
        8:  {'bezier': { 4: np.array([0.0, 0.0, -(r_bot[1] - t) * weight])}},
        9:  {'bezier': { 5: np.array([0.0, 0.0,       -r_bot[1] * weight])}},
        10: {'bezier': { 6: np.array([0.0, 0.0,       -r_bot[1] * weight])}},
        11: {'bezier': { 7: np.array([0.0, 0.0, -(r_bot[1] - t) * weight])}},

        # Top Bezier corner
        12: {'bezier': {16: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        13: {'bezier': {17: np.array([0.0, 0.0,       r_top[1] * weight])}},
        14: {'bezier': {18: np.array([0.0, 0.0,       r_top[1] * weight])}},
        15: {'bezier': {19: np.array([0.0, 0.0, (r_top[1] - t) * weight])}},
        16: {'bezier': {12: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},
        17: {'bezier': {13: np.array([      r_top[0] * weight, 0.0, 0.0])}},
        18: {'bezier': {14: np.array([      r_top[0] * weight, 0.0, 0.0])}},
        19: {'bezier': {15: np.array([(r_top[0] - t) * weight, 0.0, 0.0])}},

        # Unconnected end
        20: {'discard': True},
        21: {'discard': True},
        22: {'discard': True},
        23: {'discard': True}
    }
    edges = [
        # Bottom
        [0, 1, 2, 3, 0],
        [4, 5, 6, 7, 4],
        # Medium
        [8, 9, 10, 11, 8],
        # Top
        [12, 13, 14, 15, 12],
        [16, 17, 18, 19, 16],
        # Bottom sides
        [0, 4], [1, 5], [2, 6], [3, 7],
        # Corner sides
        [4, 8], [5, 9], [6, 10], [7, 11],
        # Medium sides
        [8, 12], [9, 13], [10, 14], [11, 15],
        # Top sides
        [12, 16], [13, 17], [14, 18], [15, 19],
        # Unconnected end
        [20, 21, 22, 23, 20],
        [16, 20], [17, 21], [18, 22], [19, 23]
    ]
    edge_attributes = {
        # Bottom corner
        (4, 8):  {'resolution': slope_resolution},
        (5, 9):  {'resolution': slope_resolution},
        (6, 10): {'resolution': slope_resolution},
        (7, 11): {'resolution': slope_resolution},

        # Top corner
        (12, 16): {'resolution': slope_resolution},
        (13, 17): {'resolution': slope_resolution},
        (14, 18): {'resolution': slope_resolution},
        (15, 19): {'resolution': slope_resolution}
    }
    faces = [
        # Bottom side
        [0, 1, 2, 3],
        # Bottom
        [4, 5, 1, 0], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3],
        # Bottom corner
        [8, 9, 5, 4], [9, 10, 6, 5], [10, 11, 7, 6], [11, 8, 4, 7],
        # Medium
        [12, 13, 9, 8], [13, 14, 10, 9], [14, 15, 11, 10], [15, 12, 8, 11],
        # Top
        [16, 17, 13, 12], [17, 18, 14, 13], [18, 19, 15, 14], [19, 16, 12, 15]
    ]

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (5.0 / 6.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes,
        edge_attributes=edge_attributes
    )
    return bezier.patch_to_mesh(body.build())


def make_flat_pin_mesh(pin_shape_size, pin_length, end_slope, edge_resolution, line_resolution):
    chamfer = min(pin_shape_size) / 10.0
    t_half = pin_shape_size[1] / 2.0
    width = pin_shape_size[0] / 2.0

    x_pos = []
    x_pos.append(pin_length)
    x_pos.append(0.0)
    x_pos.append(-pin_length)

    xz_off = [np.array([0.0, t_half])] * 3
    xz_off[1] = t_half * np.array([-math.sin(end_slope), 1.0])

    vertices = []
    for i, pos in enumerate(x_pos):
        vertices.append(np.array([pos - xz_off[i][0],  width, t_half - xz_off[i][1]]))
        vertices.append(np.array([pos + xz_off[i][0],  width, t_half + xz_off[i][1]]))
        vertices.append(np.array([pos + xz_off[i][0], -width, t_half + xz_off[i][1]]))
        vertices.append(np.array([pos - xz_off[i][0], -width, t_half - xz_off[i][1]]))

    vertex_attributes = {
         8: {'discard': True},
         9: {'discard': True},
        10: {'discard': True},
        11: {'discard': True}
    }

    edges = []
    for i in range(len(x_pos)):
        edges.append(list(range(i * 4, (i + 1) * 4)) + [i * 4])
        if i > 0:
            edges.extend([(i - 1) * 4 + j, i * 4 + j] for j in range(4))

    faces = [[0, 1, 2, 3]]
    for i in range(len(x_pos) - 2):
        faces.append([i * 4 + 1, i * 4 + 0, (i + 1) * 4 + 0, (i + 1) * 4 + 1])
        faces.append([i * 4 + 2, i * 4 + 1, (i + 1) * 4 + 1, (i + 1) * 4 + 2])
        faces.append([i * 4 + 3, i * 4 + 2, (i + 1) * 4 + 2, (i + 1) * 4 + 3])
        faces.append([i * 4 + 0, i * 4 + 3, (i + 1) * 4 + 3, (i + 1) * 4 + 0])

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (2.0 / 3.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes
    )
    return bezier.patch_to_mesh(body.build())


def make_pin_mesh(pin_shape_size, pin_height, pin_length, pin_slope, end_slope,
                  edge_resolution, line_resolution, slope_resolution):
    outer_radius_k = 0.35
    inner_radius_k = 0.3
    x_mean = pin_length * 0.45
    z_mean = pin_height * 0.5

    chamfer = min(pin_shape_size) / 10.0
    slope_cos = math.cos(pin_slope)
    slope_sin = math.sin(pin_slope)
    slope_tan = math.tan(pin_slope)
    t_half = pin_shape_size[1] / 2.0
    weight = curves.calc_bezier_weight(angle=math.pi / 2.0 - pin_slope)
    width = pin_shape_size[0] / 2.0

    rad_limit = min(pin_height, pin_length)
    outer_rad = outer_radius_k * rad_limit
    inner_rad = inner_radius_k * rad_limit

    slope_off_xz = t_half * np.array([slope_cos, slope_sin])
    end_off_xz = t_half * np.array([-math.sin(end_slope), math.cos(end_slope)])
    outer_off = z_mean - t_half - outer_rad * (1.0 - slope_sin)
    inner_off = z_mean - inner_rad * (1.0 - slope_sin)

    z_pos = [None] * 7
    z_pos[0] = t_half
    z_pos[1] = z_pos[0]
    z_pos[2] = z_mean - outer_off
    z_pos[3] = z_mean + inner_off
    z_pos[4] = pin_height
    z_pos[5] = z_pos[4]
    z_pos[6] = z_pos[5]

    x_pos = [None] * 7
    x_pos[0] = pin_length
    x_pos[1] = x_mean + outer_off * slope_tan + outer_rad * slope_cos
    x_pos[2] = x_mean + outer_off * slope_tan
    x_pos[3] = x_mean - inner_off * slope_tan
    x_pos[4] = x_mean - inner_off * slope_tan - inner_rad * slope_cos
    x_pos[5] = 0.0
    x_pos[6] = -pin_length

    if x_pos[1] >= x_pos[0]:
        raise ValueError()
    if x_pos[4] <= -end_off_xz[0]:
        raise ValueError()

    xz_off = [np.array([0.0, t_half])] * 7
    xz_off[2] = slope_off_xz
    xz_off[3] = slope_off_xz
    xz_off[5] = end_off_xz

    vertices = []
    for i, pos in enumerate(x_pos):
        vertices.append(np.array([pos - xz_off[i][0],  width, z_pos[i] - xz_off[i][1]]))
        vertices.append(np.array([pos + xz_off[i][0],  width, z_pos[i] + xz_off[i][1]]))
        vertices.append(np.array([pos + xz_off[i][0], -width, z_pos[i] + xz_off[i][1]]))
        vertices.append(np.array([pos - xz_off[i][0], -width, z_pos[i] - xz_off[i][1]]))

    slope_vec = np.array([x_pos[3] - x_pos[2], 0.0, z_pos[3] - z_pos[2]])
    dir_vec = np.array([1.0, 0.0, 0.0])

    cross = curves.get_closest_point(vertices[4], dir_vec, vertices[8], slope_vec)
    bot_beg_outer = np.array([cross[0] - vertices[4][0], 0.0, cross[2] - vertices[4][2]])
    bot_end_outer = np.array([cross[0] - vertices[8][0], 0.0, cross[2] - vertices[8][2]])

    cross = curves.get_closest_point(vertices[5], dir_vec, vertices[9], slope_vec)
    bot_beg_inner = np.array([cross[0] - vertices[5][0], 0.0, cross[2] - vertices[5][2]])
    bot_end_inner = np.array([cross[0] - vertices[9][0], 0.0, cross[2] - vertices[9][2]])

    cross = curves.get_closest_point(vertices[16], dir_vec, vertices[12], slope_vec)
    top_beg_outer = np.array([cross[0] - vertices[12][0], 0.0, cross[2] - vertices[12][2]])
    top_end_outer = np.array([cross[0] - vertices[16][0], 0.0, cross[2] - vertices[16][2]])

    cross = curves.get_closest_point(vertices[17], dir_vec, vertices[13], slope_vec)
    top_beg_inner = np.array([cross[0] - vertices[13][0], 0.0, cross[2] - vertices[13][2]])
    top_end_inner = np.array([cross[0] - vertices[17][0], 0.0, cross[2] - vertices[17][2]])

    vertex_attributes = {
         4: {'bezier': { 8: bot_beg_outer * weight}},
         5: {'bezier': { 9: bot_beg_inner * weight}},
         6: {'bezier': {10: bot_beg_inner * weight}},
         7: {'bezier': {11: bot_beg_outer * weight}},
         8: {'bezier': { 4: bot_end_outer * weight}},
         9: {'bezier': { 5: bot_end_inner * weight}},
        10: {'bezier': { 6: bot_end_inner * weight}},
        11: {'bezier': { 7: bot_end_outer * weight}},

        12: {'bezier': {16: top_beg_outer * weight}},
        13: {'bezier': {17: top_beg_inner * weight}},
        14: {'bezier': {18: top_beg_inner * weight}},
        15: {'bezier': {19: top_beg_outer * weight}},
        16: {'bezier': {12: top_end_outer * weight}},
        17: {'bezier': {13: top_end_inner * weight}},
        18: {'bezier': {14: top_end_inner * weight}},
        19: {'bezier': {15: top_end_outer * weight}},

        24: {'discard': True},
        25: {'discard': True},
        26: {'discard': True},
        27: {'discard': True}
    }

    edges = []
    for i in range(len(x_pos)):
        edges.append(list(range(i * 4, (i + 1) * 4)) + [i * 4])
        if i > 0:
            edges.extend([(i - 1) * 4 + j, i * 4 + j] for j in range(4))

    edge_attributes = {
        ( 4,  8): {'resolution': slope_resolution},
        ( 5,  9): {'resolution': slope_resolution},
        ( 6, 10): {'resolution': slope_resolution},
        ( 7, 11): {'resolution': slope_resolution},

        (12, 16): {'resolution': slope_resolution},
        (13, 17): {'resolution': slope_resolution},
        (14, 18): {'resolution': slope_resolution},
        (15, 19): {'resolution': slope_resolution}
    }

    faces = [[0, 1, 2, 3]]
    for i in range(len(x_pos) - 2):
        faces.append([i * 4 + 1, i * 4 + 0, (i + 1) * 4 + 0, (i + 1) * 4 + 1])
        faces.append([i * 4 + 2, i * 4 + 1, (i + 1) * 4 + 1, (i + 1) * 4 + 2])
        faces.append([i * 4 + 3, i * 4 + 2, (i + 1) * 4 + 2, (i + 1) * 4 + 3])
        faces.append([i * 4 + 0, i * 4 + 3, (i + 1) * 4 + 3, (i + 1) * 4 + 0])

    body = bezier.BezierObject(
        vertices=vertices,
        edges=edges,
        faces=faces,
        chamfer=chamfer,
        sharpness=math.pi * (2.0 / 3.0),
        edge_resolution=edge_resolution,
        line_resolution=line_resolution,
        vertex_attributes=vertex_attributes,
        edge_attributes=edge_attributes
    )
    return bezier.patch_to_mesh(body.build())


def find_nearest(point, group):
    if not group:
        raise ValueError()
    if len(group) == 1:
        return 0

    min_distance = None
    min_index = None
    for i, value in enumerate(group):
        distance = np.linalg.norm(value - point)
        if min_distance is None or distance < min_distance:
            min_distance = distance
            min_index = i
    return min_index


def slice_connect_direct(slices, inversion):
    mesh = model.Mesh()

    number = len(slices[0])
    for points in slices:
        mesh.geo_vertices.extend(points)

    for i in range(len(slices) - 1):
        for j in range(number - 1):
            poly = [
                i * number + j,
                (i + 1) * number + j,
                (i + 1) * number + j + 1,
                i * number + j + 1
            ]
            if inversion:
                poly.reverse()
            mesh.geo_polygons.append(poly)

    return mesh


def slice_connect_nearest(slices, inversion, closed=True):
    mesh = model.Mesh()

    start_offset = len(mesh.geo_vertices)
    mesh.geo_vertices.extend(slices[0])
    for i in range(1, len(slices)):
        slice_offset = len(mesh.geo_vertices)
        mesh.geo_vertices.extend(slices[i])
        range_length = slice_offset - start_offset - (0 if closed else 1)

        for j in range(range_length):
            j_next = (j + 1) % (slice_offset - start_offset)

            if not closed and j == 0:
                nearest_0 = 0
            else:
                nearest_0 = find_nearest(slices[i - 1][j], slices[i])
            if not closed and j == range_length - 1:
                nearest_1 = len(slices[i]) - 1
            else:
                nearest_1 = find_nearest(slices[i - 1][j_next], slices[i])

            if nearest_1 - 1 > nearest_0:
                toggle = False
                while nearest_0 < nearest_1 - 1:
                    if toggle:
                        poly = [
                            start_offset + j,
                            slice_offset + nearest_0,
                            slice_offset + nearest_0 + 1
                        ]
                        if inversion:
                            poly.reverse()
                        mesh.geo_polygons.append(poly)
                        nearest_0 += 1
                    else:
                        poly = [
                            start_offset + j_next,
                            slice_offset + nearest_1 - 1,
                            slice_offset + nearest_1
                        ]
                        if inversion:
                            poly.reverse()
                        mesh.geo_polygons.append(poly)
                        nearest_1 -= 1
                    toggle = not toggle

            if nearest_0 != nearest_1:
                poly = [
                    start_offset + j,
                    slice_offset + nearest_0,
                    slice_offset + nearest_1,
                    start_offset + j_next
                ]
                if inversion:
                    poly.reverse()
                mesh.geo_polygons.append(poly)
            else:
                poly = [
                    start_offset + j,
                    slice_offset + nearest_0,
                    start_offset + j_next
                ]
                if inversion:
                    poly.reverse()
                mesh.geo_polygons.append(poly)
        start_offset = slice_offset

    return mesh


def slice_equalize(shape, radius):
    center = model.calc_center_point(shape)
    return [model.normalize(point - center) * radius for point in shape]


def smooth_corner(point_a, point_b, point_c, count):
    if count < 3:
        raise ValueError()

    tension_beg = point_b - point_a
    tension_end = point_b - point_c
    corner = curves.Bezier(point_a, tension_beg, point_c, tension_end, count)
    return corner.tessellate()


def remove_knots(points):
    max_len_delta = 10.0
    max_smoothing = 5

    def index_distance(start, end):
        return end - start + 1 if end > start else len(points) - start + end
    def round_index(index):
        return (index + len(points)) % len(points)

    output = []
    last_point = len(points)
    skip = False
    i = 0

    while i < last_point:
        edge = (points[i], points[round_index(i + 1)])

        if i + 2 >= last_point:
            if not skip:
                output.append(points[i])
            skip = False
            i += 1
            continue

        last_index = None
        last_intersection = None
        for j in range(i + 2, len(points) - 1):
            check_edge = (points[round_index(j)], points[round_index(j + 1)])
            line_intersection = curves.intersect_lines(edge, check_edge)
            if line_intersection is not None:
                last_index = j
                last_intersection = line_intersection
                if i == 0:
                    last_point = j
                    break
                continue

        if last_index is not None:
            j = last_index
            cross_point = np.array([*last_intersection, 0.0])

            prev_len = np.linalg.norm(cross_point - points[i])
            next_len = np.linalg.norm(points[round_index(j + 1)] - cross_point)
            skipped_points = index_distance(i, j)

            if output and next_len > prev_len * max_len_delta:
                # Merge with previous point
                del output[-1]
                skipped_points += 1
                smooth_beg = points[round_index(i - 1)]
                smooth_end = points[round_index(j + 1)]
                i = j + 1
            elif prev_len > next_len * max_len_delta:
                # Merge with next point
                if skip:
                    del output[-1]
                skipped_points += 1
                smooth_beg = points[i]
                smooth_end = points[round_index(j + 2)]
                i = j + 2
            else:
                if i == 0:
                    # Collision of first segment and one of the end segments
                    smooth_beg = points[round_index(j)]
                    smooth_end = points[i + 1]
                    i = i + 1
                else:
                    if skip:
                        del output[-1]
                    smooth_beg = points[i]
                    smooth_end = points[round_index(j + 1)]
                    i = j + 1
            skip = True

            smoothed_points = smooth_corner(smooth_beg, cross_point, smooth_end,
                                            min(skipped_points, max_smoothing))
            output.extend(smoothed_points)
            continue

        if not skip:
            output.append(points[i])
        skip = False
        i += 1

    return output


def simple_scale(shape, offset):
    center = model.calc_center_point(shape)
    bottom, top = model.calc_bounding_box(shape)
    size = top - bottom

    scale = np.array([
        1.0 - offset[0] / size[0] if size[0] != 0.0 else 1.0,
        1.0 - offset[1] / size[1] if size[1] != 0.0 else 1.0,
        1.0 - offset[2] / size[2] if size[2] != 0.0 else 1.0
    ])
    return [(center - point) * scale for point in shape]


def smart_scale(points, offset, center=np.zeros(3)):
    last_point = len(points)
    if model.Mesh.isclose(points[0], points[-1]):
        last_point -= 1

    def round_index(index):
        return index % last_point

    output = []
    for i in range(last_point):
        vec_a = model.normalize(points[round_index(i - 1)] - points[i])
        vec_b = model.normalize(points[round_index(i + 1)] - points[i])
        det = np.linalg.det(np.array([vec_a[:2], vec_b[:2]]))
        dot = np.dot(vec_a, vec_b)

        if abs(dot) == 1.0:
            vec = model.normalize(center - points[i]) * offset
        else:
            vec = model.normalize(vec_a + vec_b) * offset
            if det < 0:
                vec = -vec
        output.append(points[i] + vec)

    return remove_knots(output)
