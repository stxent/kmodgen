#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# fp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import inspect
import json
import os
import sys

import exporter_kicad
import exporter_kicad_pretty

from footprints import *


class Autogen:
    MODE_KICAD, MODE_KICAD_PRETTY = range(0, 2)

    def __init__(self, parts, specs, mode, models, name, path=None, verbose=False):
        self.types = Autogen.load()
        self.verbose = verbose
        self.parts = []

        if path is not None and path[-1] != "/":
            path += "/"
        if mode == Autogen.MODE_KICAD:
            self.converter = exporter_kicad.Converter(name + "/", path, name, models)
        elif mode == Autogen.MODE_KICAD_PRETTY:
            self.converter = exporter_kicad_pretty.Converter(name + "/", path, name, models)
        else:
            raise Exception()

        for part in parts:
            for group in self.types:
                if group.__name__ == part["package"]["type"]:
                    self.parts.append(group(specs[part["package"]["spec"]], part))

        self.parts.sort(key=lambda x: x.name)

    def generate(self):
        out = self.converter.generateLibrary(self.parts, self.verbose)
        if out is not None:
            print(out)

    @staticmethod
    def load():
        builders = [entry[1] for entry in inspect.getmembers(sys.modules["footprints"])
                if inspect.ismodule(entry[1]) and entry[1].__name__.startswith("footprints.")]
        types = []
        [types.extend(entry.__dict__["types"]) for entry in builders]
        return types


parser = argparse.ArgumentParser()
parser.add_argument("-d", dest="debug", help="show debug information", default=False, action="store_true")
parser.add_argument("-i", dest="input", help="input file with descriptors", default=None)
parser.add_argument("-f", dest="models", help="model file format", default="x3d")
parser.add_argument("-o", dest="output", help="write footprints to specified directory", default=None)
parser.add_argument("-p", dest="pretty", help="use S-Expression format", default=False, action="store_true")
parser.add_argument("-s", dest="specs", help="silkscreen specifications", default=None)
options = parser.parse_args()

if options.input is None:
    raise Exception()

description = json.loads(open(options.input, "rb").read())
if "library" not in description.keys() and "parts" not in description.keys():
    raise Exception()
specs = description["specs"] if options.specs is None else json.loads(open(options.specs, "rb").read())
parts = description["parts"]
name = description["library"]
mode = Autogen.MODE_KICAD_PRETTY if options.pretty else Autogen.MODE_KICAD

Autogen(parts, specs, mode, options.models, name, options.output, options.debug).generate()
