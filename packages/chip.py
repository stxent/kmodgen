#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# chip.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import math
import numpy

import primitives
from packages import generic


class ChipBase:
    DEFAULT_CHAMFER = primitives.hmils(0.1)

    def __init__(self, material):
        self.material = material

    @staticmethod
    def make_chip(body_size, lead_width, chamfer, edge_resolution, line_resolution):
        case_chamfer = chamfer / (2.0 * math.sqrt(2.0))

        lead_size = numpy.array([lead_width, body_size[1], body_size[2]])
        ceramic_size = numpy.array([
            body_size[0] - 2.0 * lead_width,
            body_size[1] - 2.0 * case_chamfer,
            body_size[2] - 2.0 * case_chamfer])

        leads = primitives.make_chip_leads(case_size=ceramic_size, lead_size=lead_size,
            case_chamfer=case_chamfer, lead_chamfer=chamfer,
            edge_resolution=edge_resolution, line_resolution=line_resolution)
        leads.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))
        body = primitives.make_chip_body(size=ceramic_size, chamfer=case_chamfer,
            edge_resolution=edge_resolution, line_resolution=line_resolution)
        body.translate(numpy.array([0.0, 0.0, body_size[2] / 2.0]))

        return [body, leads]

    def generate(self, materials, resolutions, _, descriptor):
        body_size = primitives.hmils(numpy.array(descriptor['body']['size']))
        lead_width = primitives.hmils(descriptor['pins']['width'])
        chamfer_from_size = min(body_size[1] * 0.1, body_size[2] * 0.1)

        meshes = ChipBase.make_chip(
            body_size=body_size,
            lead_width=lead_width,
            chamfer=max(chamfer_from_size, ChipBase.DEFAULT_CHAMFER),
            edge_resolution=resolutions['edge'],
            line_resolution=resolutions['line']
        )

        if f'{self.material}.Ceramic' in materials:
            meshes[0].appearance().material = materials[f'{self.material}.Ceramic']
        if f'{self.material}.Lead' in materials:
            meshes[1].appearance().material = materials[f'{self.material}.Lead']
        return meshes

        return meshes


class ChipCapacitor(ChipBase):
    def __init__(self):
        super().__init__('Capacitor')


class ChipFerrite(ChipBase):
    def __init__(self):
        super().__init__('Ferrite')


class ChipInductor(ChipBase):
    def __init__(self):
        super().__init__('Ferrite') # XXX


types = [
    ChipCapacitor,
    ChipFerrite,
    ChipInductor
]
