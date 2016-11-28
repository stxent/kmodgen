#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fp.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import json
import os

import exporter_kicad
import exporter_kicad_pretty
import fp_qfp
import fp_sop


class Autogen:
    MODE_KICAD, MODE_KICAD_PRETTY = range(0, 2)

    def __init__(self, parts, specs, mode, models, name, path=None):
        self.groups = Autogen.loadGroups()
        self.parts = []

        if mode == Autogen.MODE_KICAD:
            self.converter = exporter_kicad.Converter(name + "/")
        elif mode == Autogen.MODE_KICAD_PRETTY:
            self.converter = exporter_kicad_pretty.Converter(name + "/", path, name, models)
        else:
            raise Exception()

        for part in parts:
            for group in self.groups:
                if group.__name__ == part["footprint"]["group"]:
                    self.parts.append(group(specs[part["footprint"]["spec"]], part))

        self.parts.sort(key=lambda x: x.name)

    def text(self):
        return self.converter.generateDocument(self.parts)

    @staticmethod
    def loadGroups():
        result = []
        result.extend(fp_qfp.groups)
        result.extend(fp_sop.groups)
        return result


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
