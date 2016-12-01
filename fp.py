#!/usr/bin/env python
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

    def __init__(self, parts, specs, mode, models, name, path=None):
        self.types = Autogen.load()
        self.parts = []

        if mode == Autogen.MODE_KICAD:
            self.converter = exporter_kicad.Converter(name + "/")
        elif mode == Autogen.MODE_KICAD_PRETTY:
            self.converter = exporter_kicad_pretty.Converter(name + "/", path, name, models)
        else:
            raise Exception()

        for part in parts:
            for group in self.types:
                if group.__name__ == part["package"]["type"]:
                    self.parts.append(group(specs[part["package"]["spec"]], part))

        self.parts.sort(key=lambda x: x.name)

    def text(self):
        return self.converter.generateDocument(self.parts)

    @staticmethod
    def load():
        builders = [entry[1] for entry in inspect.getmembers(sys.modules["footprints"])
                if inspect.ismodule(entry[1]) and entry[1].__name__.startswith("footprints.")]
        types = []
        [types.extend(entry.__dict__["types"]) for entry in builders]
        return types


parser = argparse.ArgumentParser()
parser.add_argument("-i", dest="input", help="input file with descriptors", default="")
parser.add_argument("-f", dest="models", help="model file format", default="wrl")
parser.add_argument("-l", dest="library", help="library name", default="")
parser.add_argument("-o", dest="output", help="write footprints to specified directory", default=None)
parser.add_argument("-p", dest="pretty", help="use S-Expression format", default=False, action="store_true")
parser.add_argument("-s", dest="specs", help="silkscreen specifications", default="")
options = parser.parse_args()

if options.input == "":
    raise Exception()
if options.library == "":
    raise Exception()

if options.specs != "":
    specsFile = options.specs
else:
    specsFile = os.path.dirname(os.path.realpath(__file__)) + "/descriptions/specs.json"
specs = json.loads(open(specsFile, "rb").read())

parts = json.loads(open(options.input, "rb").read())["parts"]
mode = Autogen.MODE_KICAD_PRETTY if options.pretty else Autogen.MODE_KICAD

print Autogen(parts, specs, mode, options.models, options.library, options.output).text()
