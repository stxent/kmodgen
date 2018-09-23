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
import re
import sys

import exporter_kicad
import exporter_kicad_pretty

from footprints import *


class Generator:
    def __init__(self, specs, libraryName=None, libraryPath=None, useLegacy=False, useVrml=False, verbose=False):
        self.legacy = useLegacy
        self.specs = specs
        self.verbose = verbose
        self.types = Generator.load()

        self.libraryPath = libraryPath
        self.libraryName = libraryName if libraryName is not None else 'untitled'

        modelPath = self.libraryName
        modelType = 'wrl' if useVrml else 'x3d'

        if self.legacy:
            self.converter = exporter_kicad.Converter(modelPath, modelType)
        else:
            self.converter = exporter_kicad_pretty.Converter(modelPath, modelType)

    def generate(self, parts, pattern):
        footprints = []
        for footprint in filter(lambda x: pattern.search(x['title']) is not None, parts):
            package = next(filter(lambda x: x.__name__ == footprint['package']['type'], self.types), None)
            if package is not None:
                footprints.append(package(self.specs[footprint['package']['spec']], footprint))
        footprints.sort(key=lambda x: x.name)

        if self.libraryPath is not None:
            dirExtension = '.obj' if self.legacy else '.pretty'
            fileExtension = '.mod.obj' if self.legacy else '.kicad_mod'

            libDirPath = os.path.join(self.libraryPath, self.libraryName + dirExtension)
            makeFilePath = lambda entry: os.path.join(libDirPath, entry.name + fileExtension)
            if not os.path.exists(libDirPath):
                os.makedirs(libDirPath)

        for footprint in footprints:
            footprintData = self.converter.generate(footprint)

            if self.libraryPath is not None:
                open(makeFilePath(footprint), 'wb').write(footprintData.encode('utf-8'))
                if self.verbose:
                    print('Footprint {:s}:{:s} was exported'.format(self.libraryName, footprints.name))
            else:
                print(footprintData)

    @staticmethod
    def load():
        builders = [entry[1] for entry in inspect.getmembers(sys.modules['footprints'])
                if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('footprints.')]
        types = []
        [types.extend(entry.__dict__['types']) for entry in builders]
        return types


parser = argparse.ArgumentParser()
parser.add_argument('-d', dest='debug', help='show debug information', default=False, action='store_true')
parser.add_argument('-f', dest='pattern', help='filter parts by name', default='.*')
parser.add_argument('-l', dest='library', help='add footprints to a specified library', default=None)
parser.add_argument('-o', dest='output', help='write footprints to a specified directory', default=None)
parser.add_argument('--legacy', dest='legacy', help='use legacy footprint format', default=False, action='store_true')
parser.add_argument('--specs', dest='specs', help='override silkscreen specifications', default=None)
parser.add_argument('--vrml', dest='vrml', help='use VRML model format', default=False, action='store_true')
parser.add_argument(dest='files', nargs='*')
options = parser.parse_args()

for filename in options.files:
    desc = json.load(open(filename, 'rb'))
    specs = desc['specs'] if options.specs is None else json.load(open(options.specs, 'rb'))
    pattern = re.compile(options.pattern, re.S)
    generator = Generator(specs, options.library, options.output, options.legacy, options.vrml, options.debug)
    generator.generate(desc['parts'], pattern)
