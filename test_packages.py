#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_packages.py
# Copyright (C) 2026 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import json
import math

import mod
from packages import chip
from packages import crystals
from packages import inductors
from packages import qfn
from packages import qfp
from packages import smd
from packages import sop
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

def verify_models(meshes, destination_path, source_name):
    serialized = serialize_models(meshes, destination_path, source_name)
    assert compare_models(source_name, serialized) is True


class TestCapacitor:
    FILE_PACKAGE_CAP_BENT_LEADS = 'test_package_cap_bent_leads.x3d'
    FILE_PACKAGE_CAP_BENT_FORKED_LEADS = 'test_package_cap_bent_forked_leads.x3d'

    @staticmethod
    def make_bent_leads(is_forked):
        if is_forked:
            descriptor = {
                'body': {'size': [3.5, 2.8, 1.9]},
                'pins': {'size': [0.8, 2.2, 1.0], 'thickness': 0.1, 'fork': True},
            }
        else:
            descriptor = {
                'body': {'size': [4.3, 2.6, 2.2]},
                'pins': {'size': [1.08, 1.42, 1.1], 'length': 0.4, 'thickness': 0.2}
            }

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'BentLeadsCapacitor.Strip': 'DebugGreen',
            'BentLeadsCapacitor.Plastic': 'DebugBlue',
            'BentLeadsCapacitor.Lead': 'DebugYellow'
        })
        resolutions = {
            'arc': 6,
            'chamfer': 1,
            'edge': 3,
            'line': 1
        }

        generator = chip.BentLeadsCapacitor()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_cap_bent_leads(self, tmp_path):
        model.reset_allocator()
        meshes = TestCapacitor.make_bent_leads(False)
        verify_models(meshes, tmp_path, TestCapacitor.FILE_PACKAGE_CAP_BENT_LEADS)

    def test_package_cap_bent_forked_leads(self, tmp_path):
        model.reset_allocator()
        meshes = TestCapacitor.make_bent_leads(True)
        verify_models(meshes, tmp_path, TestCapacitor.FILE_PACKAGE_CAP_BENT_FORKED_LEADS)


class TestCrystal:
    FILE_PACKAGE_CRYSTAL_2PIN = 'test_package_crystal_2pin.x3d'
    FILE_PACKAGE_CRYSTAL_4PIN = 'test_package_crystal_4pin.x3d'

    @staticmethod
    def make_package(pin_count):
        if pin_count == 4:
            descriptor = {
                'body': {'size': [3.2, 2.5, 0.7]},
                'pins': {'size': [1.0, 0.9], 'count': 4}
            }
        else:
            descriptor = {
                'body': {'size': [2.05, 1.2, 0.6]},
                'pins': {'size': [0.525, 1.2], 'count': 2}
            }

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'Crystal.Body': 'DebugBlue',
            'Crystal.Cap': 'DebugGreen',
            'Crystal.Lead': 'DebugYellow'
        })
        resolutions = {
            'arc': 6,
            'edge': 3,
            'line': 1
        }

        generator = crystals.CrystalMetalCapSMD()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_crystal_2pin(self, tmp_path):
        model.reset_allocator()
        meshes = TestCrystal.make_package(2)
        verify_models(meshes, tmp_path, TestCrystal.FILE_PACKAGE_CRYSTAL_2PIN)

    def test_package_crystal_4pin(self, tmp_path):
        model.reset_allocator()
        meshes = TestCrystal.make_package(4)
        verify_models(meshes, tmp_path, TestCrystal.FILE_PACKAGE_CRYSTAL_4PIN)


class TestLED:
    FILE_PACKAGE_LED_PLAIN = 'test_package_led_plain.x3d'
    FILE_PACKAGE_LED_ROUND = 'test_package_led_round.x3d'

    @staticmethod
    def make_package(is_plain):
        if is_plain:
            descriptor = {
                'body': {'size': [1.0, 0.5, 0.5], 'lens': [0.8, 0.5, 0.35], 'plain': True},
                'pins': {'length': 0.1},
                'mark': {'width': 0.1}
            }
        else:
            descriptor = {
                'body': {'size': [2.0, 1.25, 0.8], 'lens': [1.2, 1.25, 0.5]},
                'pins': {'length': 0.4},
                'mark': {'width': 0.2}
            }

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'LED.Body': 'DebugBlue',
            'LED.Cap': 'DebugTransparent',
            'LED.Crystal': 'DebugGreen',
            'LED.Lead': 'DebugYellow',
            'LED.Mark': 'DebugRed'
        })
        resolutions = {
            'arc': 6,
            'chamfer': 1,
            'edge': 3,
            'line': 1
        }

        generator = chip.ChipLED()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_led_plain(self, tmp_path):
        model.reset_allocator()
        meshes = TestLED.make_package(True)
        verify_models(meshes, tmp_path, TestLED.FILE_PACKAGE_LED_PLAIN)

    def test_package_led_round(self, tmp_path):
        model.reset_allocator()
        meshes = TestLED.make_package(False)
        verify_models(meshes, tmp_path, TestLED.FILE_PACKAGE_LED_ROUND)


class TestDFN:
    FILE_PACKAGE_DFN = 'test_package_dfn.x3d'
    FILE_PACKAGE_DFN_HEATSINK = 'test_package_dfn_heatsink.x3d'

    @staticmethod
    def make_package(has_heatsink):
        descriptor = {
            'body': {'size': [3.0, 3.0, 1.1]},
            'mark': {'radius': 0.25},
            'pins': {'count': 6, 'pitch': 1.0, 'length': 0.4, 'width': 0.4}
        }
        if has_heatsink:
            descriptor['heatsink'] = {'size': [2.4, 1.5]}

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'DFN.Dot': 'DebugRed',
            'DFN.Plastic': 'DebugBlue',
            'DFN.Lead': 'DebugYellow'
        })
        resolutions = {
            'chamfer': 1,
            'circle': 24,
            'line': 1
        }

        generator = qfn.DFN()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_dfn(self, tmp_path):
        model.reset_allocator()
        meshes = TestDFN.make_package(False)
        verify_models(meshes, tmp_path, TestDFN.FILE_PACKAGE_DFN)

    def test_package_dfn_heatsink(self, tmp_path):
        model.reset_allocator()
        meshes = TestDFN.make_package(True)
        verify_models(meshes, tmp_path, TestDFN.FILE_PACKAGE_DFN_HEATSINK)


class TestQFN:
    FILE_PACKAGE_QFN = 'test_package_qfn.x3d'
    FILE_PACKAGE_QFN_HEATSINK = 'test_package_qfn_heatsink.x3d'

    @staticmethod
    def make_package(has_heatsink, has_mark):
        descriptor = {
            'body': {'size': [4.0, 4.0, 0.75]},
            'pins': {
                'columns': 6,
                'rows': 6,
                'pitch': 0.5,
                'height': 0.2,
                'length': 0.4,
                'width': 0.25
            }
        }
        if has_heatsink:
            descriptor['heatsink'] = {'size': [2.8, 2.8]}
        if not has_mark:
            descriptor['mark'] = {'dot': False}

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'QFN.Dot': 'DebugRed',
            'QFN.Plastic': 'DebugBlue',
            'QFN.Lead': 'DebugYellow'
        })
        resolutions = {
            'chamfer': 1,
            'circle': 24,
            'line': 1
        }

        generator = qfn.QFN()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_qfn(self, tmp_path):
        model.reset_allocator()
        meshes = TestQFN.make_package(False, True)
        verify_models(meshes, tmp_path, TestQFN.FILE_PACKAGE_QFN)

    def test_package_qfn_heatsink(self, tmp_path):
        model.reset_allocator()
        meshes = TestQFN.make_package(True, False)
        verify_models(meshes, tmp_path, TestQFN.FILE_PACKAGE_QFN_HEATSINK)


class TestQFP:
    FILE_PACKAGE_QFP = 'test_package_qfp.x3d'

    @staticmethod
    def make_package():
        descriptor = {
            'body': {'size': [7.0, 7.0, 1.4]},
            'pins': {'shape': [0.35, 0.15], 'length': 1.0, 'columns': 8, 'rows': 8, 'pitch': 0.8}
        }

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'QFP.Dot': 'DebugRed',
            'QFP.Plastic': 'DebugBlue',
            'QFP.Lead': 'DebugYellow'
        })
        resolutions = {
            'chamfer': 2,
            'circle': 24,
            'edge': 3,
            'line': 1
        }

        generator = qfp.QFP()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_qfp(self, tmp_path):
        model.reset_allocator()
        meshes = TestQFP.make_package()
        verify_models(meshes, tmp_path, TestQFP.FILE_PACKAGE_QFP)


class TestSOP:
    FILE_PACKAGE_SOP = 'test_package_sop.x3d'
    FILE_PACKAGE_SOP_HEATSINK = 'test_package_sop_heatsink.x3d'

    @staticmethod
    def make_package(has_heatsink):
        descriptor = {
            'body': {'size': [6.5, 4.4, 1.2]},
            'pins': {'shape': [0.245, 0.15], 'length': 1.0, 'count': 20, 'pitch': 0.65}
        }
        if has_heatsink:
            descriptor['heatsink'] = {'size': [3.7, 2.4]}

        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'SOP.Plastic': 'DebugBlue',
            'SOP.Lead': 'DebugYellow'
        })
        resolutions = {
            'chamfer': 2,
            'edge': 3,
            'line': 2 if has_heatsink else 1
        }

        generator = sop.SOP()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    def test_package_sop(self, tmp_path):
        model.reset_allocator()
        meshes = TestSOP.make_package(False)
        verify_models(meshes, tmp_path, TestSOP.FILE_PACKAGE_SOP)

    def test_package_sop_heatsink(self, tmp_path):
        model.reset_allocator()
        meshes = TestSOP.make_package(True)
        verify_models(meshes, tmp_path, TestSOP.FILE_PACKAGE_SOP_HEATSINK)


class TestSOT:
    FILE_PACKAGE_SOT = 'test_package_sot.x3d'
    FILE_PACKAGE_SOT_FLAT = 'test_package_sot_flat.x3d'
    FILE_PACKAGE_SOT_STRIP = 'test_package_sot_strip.x3d'

    @staticmethod
    def make_package(descriptor):
        materials = mod.load_materials(json.load(open('config.json', 'rb')), {
            'SOT.Mark': 'DebugRed',
            'SOT.Plastic': 'DebugBlue',
            'SOT.Lead': 'DebugYellow'
        })
        resolutions = {
            'chamfer': 2,
            'circle': 24,
            'edge': 3,
            'line': 1
        }

        generator = smd.SOT()
        meshes = generator.generate(materials, resolutions, None, descriptor)
        for mesh in meshes:
            mesh.appearance().solid = True
        return meshes

    @staticmethod
    def make_package_default():
        descriptor = {
            'body': {'size': [2.2, 1.35, 1.0]},
            'pins': {
                'count': 6,
                'pitch': 0.65,
                'slope': 5.0,

                'default': {'shape': [0.25, 0.175], 'length': 0.425},
                '5': None
            }
        }
        return TestSOT.make_package(descriptor)

    @staticmethod
    def make_package_flat():
        descriptor = {
            'band': {'offset': -0.095},
            'body': {'size': [1.6, 1.2, 0.55]},
            'pins': {
                'count': 6,
                'flat': True,
                'pitch': 0.5,

                'default': {'shape': [0.22, 0.13], 'length': 0.2}
            },
            'mark': {'dot': True}
        }
        return TestSOT.make_package(descriptor)

    @staticmethod
    def make_package_strip():
        descriptor = {
            'band': {'offset': 0.12},
            'body': {'size': [1.8, 1.35, 1.0]},
            'pins': {
                'count': 2,
                'slope': 5.0,

                'default': {'shape': [0.33, 0.18], 'length': 0.45}
            },
            'mark': {'dot': True, 'strip': True}
        }
        return TestSOT.make_package(descriptor)

    def test_package_sot(self, tmp_path):
        model.reset_allocator()
        meshes = TestSOT.make_package_default()
        verify_models(meshes, tmp_path, TestSOT.FILE_PACKAGE_SOT)

    def test_package_sot_flat(self, tmp_path):
        model.reset_allocator()
        meshes = TestSOT.make_package_flat()
        verify_models(meshes, tmp_path, TestSOT.FILE_PACKAGE_SOT_FLAT)

    def test_package_sot_strip(self, tmp_path):
        model.reset_allocator()
        meshes = TestSOT.make_package_strip()
        verify_models(meshes, tmp_path, TestSOT.FILE_PACKAGE_SOT_STRIP)
