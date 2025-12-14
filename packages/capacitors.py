#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# capacitors.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy as np

import primitives
from wrlconv import curves
from wrlconv import geometry
from wrlconv import model


class RadialCapacitor:
    def __init__(self):
        pass

    @staticmethod
    def build_bumped_cap(slices, beginning, sections, section_width, cap_radius, body_radius):
        if sections < 2:
            raise ValueError()

        if beginning:
            vertices = [slices[i][0] for i in range(0, len(slices))]
        else:
            vertices = [slices[i][-1] for i in range(0, len(slices))]

        center = sum(vertices) / len(slices)
        angle = lambda v: math.atan2((v - center)[1], (v - center)[0])
        belongs = lambda v, a, b: a <= v <= b if b >= a else v >= a or v <= b
        rot = lambda a, b: a if a < b else a - b if a >= 0 else b - a

        geo_vertices = []
        geo_polygons = []

        depth = section_width / 4.0
        first_circle_radius = section_width / 4.0 / math.sin(2.0 * math.pi / float(2 * sections))
        second_circle_radius = section_width / 2.0 / math.sin(2.0 * math.pi / float(2 * sections))
        first_circle_points, second_circle_points = [], []
        outer_points = []
        body_points = []

        for i in range(0, sections):
            direction = 2.0 * math.pi / float(sections) * float(i)
            vector = np.array([math.cos(direction), math.sin(direction), 0.0])
            first_circle_points.append(center + vector * first_circle_radius
                + np.array([0.0, 0.0, -depth]))
            second_circle_points.append(center + vector * second_circle_radius)

            direction = 2.0 * math.pi / float(sections) * (float(i) + 0.5)
            vector = np.array([
                math.cos(direction),
                math.sin(direction),
                0.0])
            normal = np.array([
                math.cos(direction + math.pi / 2.0),
                math.sin(direction + math.pi / 2.0),
                0.0])
            points = [
                center + vector * cap_radius + normal * section_width / 2.0,
                center + vector * cap_radius + normal * section_width / 4.0
                    + np.array([0.0, 0.0, -depth]),
                center + vector * cap_radius - normal * section_width / 4.0
                    + np.array([0.0, 0.0, -depth]),
                center + vector * cap_radius - normal * section_width / 2.0]
            outer_points.append(points)
            points = [
                center + vector * body_radius + normal * section_width / 2.0,
                center + vector * body_radius + normal * section_width / 4.0
                    + np.array([0.0, 0.0, -depth]),
                center + vector * body_radius - normal * section_width / 4.0
                    + np.array([0.0, 0.0, -depth]),
                center + vector * body_radius - normal * section_width / 2.0]
            body_points.append(points)

        edge_points = []
        for i in range(0, sections):
            inner_range = (outer_points[rot(i - 1, sections)][0], outer_points[i][3])
            outer_range = (outer_points[rot(i - 1, sections)][3], outer_points[i][0])
            inner = (angle(inner_range[0]), angle(inner_range[1]))
            outer = (angle(outer_range[0]), angle(outer_range[1]))

            normal_angles = (
                2.0 * math.pi / float(sections) * (float(i) + 0.5) + math.pi / 2.0,
                2.0 * math.pi / float(sections) * (float(i) - 0.5) + math.pi / 2.0)
            normals = (
                np.array([math.cos(normal_angles[0]), math.sin(normal_angles[0]), 0.0]),
                np.array([math.cos(normal_angles[1]), math.sin(normal_angles[1]), 0.0]))

            points = [v for v in vertices if belongs(angle(v), inner[0], inner[1])]

            for j, vertex in enumerate(vertices):
                seg = (vertices[rot(j - 1, len(vertices))], vertex)

                if (not belongs(angle(seg[0]), outer[0], outer[1])
                    and not belongs(angle(seg[1]), outer[0], outer[1])):
                    continue

                intersection = curves.intersect_line_plane(second_circle_points[i],
                    normals[0], seg[0], seg[1])
                if intersection is not None:
                    outer_points[i][3] = intersection
                    points.append(intersection)

                intersection = curves.intersect_line_plane(second_circle_points[i],
                    normals[1], seg[0], seg[1])
                if intersection is not None:
                    outer_points[rot(i - 1, sections)][0] = intersection
                    points.append(intersection)

            if inner[1] >= inner[0]:
                points = sorted(points, key=angle)
            else:
                points = (sorted(filter(lambda x: angle(x) >= 0.0, points), key=angle)
                    + sorted(filter(lambda x: angle(x) < 0.0, points), key=angle))
            edge_points.append(points)

        first_circle_point_func = lambda a: rot(a, sections)
        geo_vertices.extend(first_circle_points)
        second_circle_point_func = lambda a: sections + rot(a, sections)
        geo_vertices.extend(second_circle_points)
        outer_point_func = lambda a, b: 2 * sections + rot(a, sections) * 4 + rot(b, 4)
        for points in outer_points:
            geo_vertices.extend(points)
        body_point_func = lambda a, b: 6 * sections + rot(a, sections) * 4 + rot(b, 4)
        for points in body_points:
            geo_vertices.extend(points)

        for points in edge_points:
            geo_vertices.extend(points)

        def edge_indices(edge):
            index_range = range(0, len(edge_points[edge]))
            return [10 * sections + sum(map(len, edge_points[0:edge])) + i for i in index_range]

        # Central polygon
        geo_polygons.append(list(range(0, sections)))
        for i in range(0, sections):
            # Bumped polygons
            geo_polygons.append([
                first_circle_point_func(i + 1),
                first_circle_point_func(i),
                outer_point_func(i, 2),
                outer_point_func(i, 1)])
            # Ramp polygons
            geo_polygons.append([
                second_circle_point_func(i + 1),
                first_circle_point_func(i + 1),
                outer_point_func(i, 1),
                outer_point_func(i, 0)])
            geo_polygons.append([
                first_circle_point_func(i),
                second_circle_point_func(i),
                outer_point_func(i, 3),
                outer_point_func(i, 2)])
            # Arc polygons
            geo_polygons.append([second_circle_point_func(i)] + edge_indices(i))
            # Partially visible polygons
            geo_polygons.append([
                outer_point_func(i, 0),
                outer_point_func(i, 1),
                body_point_func(i, 1),
                body_point_func(i, 0)])
            geo_polygons.append([
                outer_point_func(i, 2),
                outer_point_func(i, 3),
                body_point_func(i, 3),
                body_point_func(i, 2)])
            geo_polygons.append([
                outer_point_func(i, 1),
                outer_point_func(i, 2),
                body_point_func(i, 2),
                body_point_func(i, 1)])
            geo_polygons.append([
                body_point_func(i, 0),
                body_point_func(i, 1),
                body_point_func(i, 2),
                body_point_func(i, 3)])

        # Generate object
        mesh = model.Mesh()
        mesh.geo_vertices = geo_vertices
        for patch in geo_polygons:
            mesh.geo_polygons.extend(model.Mesh.triangulate(patch))
        mesh.optimize()

        return mesh

    @staticmethod
    def build_capacitor_curve(radius, height, curvature, band_offset, cap_radius, cap_depth,
                              chamfer, edge_details, band_details):

        if cap_radius is not None and cap_depth is not None and chamfer is None:
            raise ValueError()

        weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        curve = []

        # Bottom cap
        if cap_radius is not None:
            if cap_depth is not None:
                curve.append(curves.Line(
                    (cap_radius, 0.0, cap_depth - chamfer),
                    (cap_radius, 0.0, chamfer),
                    1))
                curve.append(curves.Line(
                    (cap_radius, 0.0, chamfer),
                    (cap_radius + chamfer, 0.0, 0.0),
                    1))
                curve.append(curves.Line(
                    (cap_radius + chamfer, 0.0, 0.0),
                    (radius - curvature, 0.0, 0.0),
                    1))
            else:
                curve.append(curves.Line(
                    (cap_radius, 0.0, 0.0),
                    (radius - curvature, 0.0, 0.0),
                    1))

        # Plastic
        curve.append(curves.Bezier(
            (radius - curvature, 0.0, 0.0),
            (curvature * weight, 0.0, 0.0),
            (radius, 0.0, curvature),
            (0.0, 0.0, -curvature * weight),
            edge_details))
        curve.append(curves.Line(
            (radius, 0.0, curvature),
            (radius, 0.0, band_offset - curvature * 2.0),
            1))
        curve.append(curves.Bezier(
            (radius, 0.0, band_offset - curvature * 2.0),
            (0.0, 0.0, curvature),
            (radius - curvature, 0.0, band_offset),
            (0.0, 0.0, -curvature),
            band_details))
        curve.append(curves.Bezier(
            (radius - curvature, 0.0, band_offset),
            (0.0, 0.0, curvature),
            (radius, 0.0, band_offset + curvature * 2.0),
            (0.0, 0.0, -curvature),
            band_details))
        curve.append(curves.Line(
            (radius, 0.0, band_offset + curvature * 2.0),
            (radius, 0.0, height - curvature),
            1))
        curve.append(curves.Bezier(
            (radius, 0.0, height - curvature),
            (0.0, 0.0, curvature * weight),
            (radius - curvature, 0.0, height),
            (curvature * weight, 0.0, 0.0),
            edge_details))

        # Top cap
        if cap_radius is not None:
            if cap_depth is not None:
                curve.append(curves.Line(
                    (radius - curvature, 0.0, height),
                    (cap_radius + chamfer, 0.0, height),
                    1))
                curve.append(curves.Line(
                    (cap_radius + chamfer, 0.0, height),
                    (cap_radius, 0.0, height - chamfer),
                    1))
                curve.append(curves.Line(
                    (cap_radius, 0.0, height - chamfer),
                    (cap_radius, 0.0, height - cap_depth),
                    1))
            else:
                curve.append(curves.Line(
                    (radius - curvature, 0.0, height),
                    (cap_radius, 0.0, height),
                    1))

        return curve

    @staticmethod
    def build_pin_curve(radius, height, curvature, edge_details):
        weight = curves.calc_bezier_weight(angle=math.pi / 2.0)
        curve = []

        curve.append(curves.Bezier(
            (radius - curvature, 0.0, -height),
            (curvature * weight, 0.0, 0.0),
            (radius, 0.0, -height + curvature),
            (0.0, 0.0, -curvature * weight),
            edge_details))
        curve.append(curves.Line((radius, 0.0, curvature - height), (radius, 0.0, 0.0), 1))

        return curve

    @staticmethod
    def build_capacitor_body(curve, edges, polarized, materials, name, cap_sections,
                             cap_inner_radius, cap_outer_radius, cap_section_width, _):
        slices = curves.rotate(curve=curve, axis=np.array([0.0, 0.0, 1.0]), edges=edges)
        meshes = []

        bottom_cap = primitives.make_rotation_cap_mesh(slices=slices, inverse=True)
        bottom_cap.appearance().material = RadialCapacitor.mat(materials, 'Bottom')
        bottom_cap.ident = name + 'BottomCap'
        meshes.append(bottom_cap)

        if cap_sections == 1:
            top_cap = primitives.make_rotation_cap_mesh(slices=slices, inverse=False)
        else:
            top_cap = RadialCapacitor.build_bumped_cap(
                slices=slices,
                beginning=False,
                sections=cap_sections,
                section_width=cap_section_width,
                cap_radius=cap_inner_radius,
                body_radius=cap_outer_radius)
        top_cap.appearance().material = RadialCapacitor.mat(materials, 'Top')
        top_cap.ident = name + 'TopCap'
        meshes.append(top_cap)

        if polarized:
            body = geometry.build_rotation_mesh(slices=slices[1:], wrap=False, inverse=True)
            body.appearance().material = RadialCapacitor.mat(materials, 'Body')
            body.ident = name + 'Body'
            meshes.append(body)

            mark = geometry.build_rotation_mesh(slices=[slices[-1]] + slices[0:2], wrap=False,
                                                inverse=True)
            mark.appearance().material = RadialCapacitor.mat(materials, 'Mark')
            mark.ident = name + 'Mark'
            meshes.append(mark)
        else:
            body = geometry.build_rotation_mesh(slices=slices, wrap=True, inverse=True)
            body.appearance().material = RadialCapacitor.mat(materials, 'Body')
            body.ident = name + 'Body'
            meshes.append(body)

        return meshes

    @staticmethod
    def build_capacitor_pin(curve, edges):
        slices = curves.rotate(curve=curve, axis=(0.0, 0.0, 1.0), edges=edges)

        pin = geometry.build_rotation_mesh(slices=slices, wrap=True, inverse=True)
        pin.append(primitives.make_rotation_cap_mesh(slices=slices, inverse=True))
        pin.optimize()

        return pin

    @staticmethod
    def demangle(title):
        title = title.replace('C-', 'Cap')
        title = title.replace('CP-', 'Cap')
        title = title.replace('R-', 'Radial')
        title = title.replace('A-', 'Axial')
        return title

    @staticmethod
    def mat(materials, name):
        if f'RadialCapacitor.{name}' in materials:
            return materials[f'RadialCapacitor.{name}']

        result = model.Material()
        result.color.ident = name
        return result

    def generate(self, materials, resolutions, _, descriptor):
        title = RadialCapacitor.demangle(descriptor['title'])

        body_details = resolutions['body']
        body_edges = resolutions['circle']
        pin_edges = resolutions['wire']
        cap_sections = descriptor['caps']['sections'] if 'sections' in descriptor['caps'] else 1

        meshes = []
        body_curve = RadialCapacitor.build_capacitor_curve(
            primitives.hmils(descriptor['body']['diameter']) / 2.0,
            primitives.hmils(descriptor['body']['height']),
            primitives.hmils(descriptor['body']['curvature']),
            primitives.hmils(descriptor['body']['band']),
            primitives.hmils(descriptor['caps']['diameter']) / 2.0,
            primitives.hmils(descriptor['caps']['depth']),
            primitives.hmils(descriptor['caps']['chamfer']),
            body_details,
            body_details + 1
        )

        body_mesh = RadialCapacitor.build_capacitor_body(
            body_curve,
            body_edges,
            descriptor['body']['stripe'],
            materials,
            title,
            cap_sections,
            primitives.hmils(descriptor['caps']['diameter']) / 2.0,
            primitives.hmils(descriptor['caps']['diameter']
                             + descriptor['body']['curvature']) / 2.0,
            primitives.hmils(descriptor['body']['curvature']),
            primitives.hmils(descriptor['body']['curvature']) / 2.0
        )
        meshes.extend(body_mesh)

        pin_curve = RadialCapacitor.build_pin_curve(
            primitives.hmils(descriptor['pins']['diameter']) / 2.0,
            primitives.hmils(descriptor['pins']['height']),
            primitives.hmils(descriptor['pins']['curvature']),
            resolutions['edge']
        )

        pin_mesh = RadialCapacitor.build_capacitor_pin(pin_curve, pin_edges)
        pin_mesh.ident = title + 'Pin'
        pin_mesh.appearance().material = self.mat(materials, 'Lead')

        spacing = primitives.hmils(descriptor['pins']['spacing']) / 2.0
        pos_pin = model.Mesh(parent=pin_mesh, name=pin_mesh.ident + 'Pos')
        pos_pin.translate([-spacing, 0.0, 0.0])
        meshes.append(pos_pin)
        neg_pin = model.Mesh(parent=pin_mesh, name=pin_mesh.ident + 'Neg')
        neg_pin.translate([spacing, 0.0, 0.0])
        meshes.append(neg_pin)

        return meshes


types = [RadialCapacitor]
