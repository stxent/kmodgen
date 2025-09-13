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
    def __init__(self, library_name=None, library_path=None, use_legacy=False, use_vrml=False):
        self.legacy = use_legacy
        self.types = Generator.load()

        self.library_path = library_path
        self.library_name = library_name if library_name is not None else 'untitled'

        model_path = self.library_name
        model_type = 'wrl' if use_vrml else 'x3d'

        if self.legacy:
            self.converter = exporter_kicad.Converter(model_path, model_type)
        else:
            self.converter = exporter_kicad_pretty.Converter(model_path, model_type)

    def load_footprints(self, specs, parts, pattern):
        footprints = []
        for part in parts:
            if pattern.search(part['title']) is not None:
                for package in self.types:
                    if package.__name__ == part['package']['type']:
                        footprints.append(package(specs[part['package']['spec']], part))
        footprints.sort(key=lambda x: x.name)
        return footprints

    def generate(self, specs, parts, pattern, verbose):
        footprints = self.load_footprints(specs, parts, pattern)

        if self.library_path is not None:
            dir_extension = '.obj' if self.legacy else '.pretty'
            file_extension = '.mod.obj' if self.legacy else '.kicad_mod'

            lib_dir_path = os.path.join(self.library_path, self.library_name + dir_extension)
            make_file_path = lambda entry: os.path.join(lib_dir_path, entry.name + file_extension)
            if not os.path.exists(lib_dir_path):
                try:
                    os.makedirs(lib_dir_path)
                except FileExistsError:
                    pass

        for footprint in footprints:
            footprint_data = self.converter.generate(footprint)

            if self.library_path is not None:
                open(make_file_path(footprint), 'wb').write(footprint_data.encode('utf-8'))
                if verbose:
                    print('Footprint {:s}:{:s} was exported'.format(
                        self.library_name, footprint.name))
            else:
                print(footprint_data)

    @staticmethod
    def load():
        builders = [entry[1] for entry in inspect.getmembers(sys.modules['footprints'])
            if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('footprints.')]
        types = []
        for entry in builders:
            types.extend(entry.__dict__['types'])
        return types


def main():
    config_path = f'{os.path.dirname(os.path.realpath(__file__))}/config.json'
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', dest='config', help='path to a configuration file',
                        default=config_path)
    parser.add_argument('-d', dest='debug', help='show debug information',
                        default=False, action='store_true')
    parser.add_argument('-f', dest='pattern', help='filter parts by name',
                        default='.*')
    parser.add_argument('-l', dest='library', help='add footprints to a specified library',
                        default=None)
    parser.add_argument('-o', dest='output', help='write footprints to a specified directory',
                        default=None)
    parser.add_argument('--legacy', dest='legacy', help='use legacy footprint format',
                        default=False, action='store_true')
    parser.add_argument('--specs', dest='specs', help='override silkscreen specifications',
                        default=None)
    parser.add_argument('--vrml', dest='vrml', help='use VRML model format',
                        default=False, action='store_true')
    parser.add_argument(dest='files', nargs='*')
    options = parser.parse_args()

    for filename in options.files:
        desc = json.load(open(filename, 'rb'))
        specs = desc['specs'] if 'specs' in desc else json.load(open(options.config, 'rb'))['specs']
        pattern = re.compile(options.pattern, re.S)
        generator = Generator(options.library, options.output, options.legacy, options.vrml)
        generator.generate(specs, desc['parts'], pattern, options.debug)

if __name__ == '__main__':
    main()
