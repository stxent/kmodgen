#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# mod.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import inspect
import json
import os
import re
import sys
import numpy

from wrlconv import model
from wrlconv import vrml_export
from wrlconv import vrml_export_kicad
from wrlconv import vrml_import
from wrlconv import x3d_export
from wrlconv import x3d_import

from packages import *

def load_materials(settings, entries):
    materials = {}

    # First pass to load complete descriptions
    for key in settings['materials']:
        entry = settings['materials'][key]
        if not isinstance(entry, str):
            materials.update({key: model.Material(entry, key.capitalize())})
    # Second pass to process aliases
    for key in settings['materials']:
        entry = settings['materials'][key]
        if isinstance(entry, str):
            materials[key] = materials[entry]

    # First pass to load complete descriptions
    for key in entries:
        entry = entries[key]
        if not isinstance(entry, str):
            materials.update({key: model.Material(entry, key.capitalize())})
    # Second pass to process aliases
    for key in entries:
        entry = entries[key]
        if isinstance(entry, str):
            materials[key] = materials[entry]

    return materials

def load_models(config, files, pattern):
    builders = [entry[1] for entry in inspect.getmembers(sys.modules['packages'])
        if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('packages.')]
    types = []
    for entry in builders:
        types.extend(entry.__dict__['types'])

    models = []
    pattern_re = re.compile(pattern, re.S)

    for filename in files:
        desc = json.load(open(filename, 'rb'))

        materials = load_materials(config, desc['materials'] if 'materials' in desc else {})
        resolutions = load_resolutions(config, desc['resolutions'] if 'resolutions' in desc else {})
        templates = load_templates(desc['templates'],
                                   os.path.dirname(filename)) if 'templates' in desc else []

        for part in filter(lambda x: pattern_re.search(x['title']) is not None, desc['parts']):
            for package in types:
                if package.__name__ == part['package']['type']:
                    models.append((package().generate(materials, resolutions, templates, part),
                                  part['title']))

    return models

def load_resolutions(settings, entries):
    resolutions = settings['resolutions']

    for key in resolutions:
        if key in entries:
            resolutions[key] = entries[key]

    return resolutions

def load_templates(entries, path):
    templates = []
    for entry in entries:
        script_path = path + '/' + entry
        extension = os.path.splitext(script_path)[1][1:].lower()
        if extension == 'wrl':
            templates.extend(vrml_import.load(script_path))
        elif extension == 'x3d':
            templates.extend(x3d_import.load(script_path))
    return templates

def parse_args():
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
    parser.add_argument('-o', dest='output', help='write models to a specified directory',
                        default='')
    parser.add_argument('-v', dest='view', help='render models',
                        default=False, action='store_true')
    parser.add_argument('--fast', dest='fast', help='disable visual effects',
                        default=False, action='store_true')
    parser.add_argument('--no-grid', dest='simple', help='disable grid',
                        default=False, action='store_true')
    parser.add_argument('--normals', dest='normals', help='show normals',
                        default=False, action='store_true')
    parser.add_argument('--smooth', dest='smooth', help='use smooth shading',
                        default=False, action='store_true')
    parser.add_argument('--vrml', dest='vrml', help='use VRML model format',
                        default=False, action='store_true')
    parser.add_argument(dest='files', nargs='*')

    return parser.parse_args()

def render_models(models, is_fast, is_simple, is_debug):
    if not models:
        print('Empty set of models')
        sys.exit()

    if is_debug:
        render_ogl41.debug_enabled = True

    effects = {} if is_fast else {'antialiasing': 4}
    helper_objects = [] if is_simple else helpers.make_grid()
    export_list = []
    for entry in models:
        export_list.extend(entry[0])
    render = render_ogl41.Render(helper_objects + export_list, effects)
    render.run()

def write_models(models, library, output, is_vrml, is_debug=False):
    if library is not None:
        library_path = os.path.join(output, library)
    else:
        library_path = output
    if not os.path.exists(library_path):
        os.makedirs(library_path)

    extension = '.wrl' if is_vrml else '.x3d'
    export_func = vrml_export_kicad.store if is_vrml else x3d_export.store
    for group in models:
        export_func(group[0], os.path.join(library_path, group[1] + extension))
        if is_debug:
            print('Model {:s}:{:s} was exported'.format(group[1], extension))

def main(options):
    config = json.load(open(options.config, 'rb'))
    models = load_models(config, options.files, options.pattern)

    if options.output != '':
        write_models(models, options.library, options.output, options.vrml, options.debug)

    if options.normals or options.smooth:
        for group in models:
            for entry in group[0]:
                entry.appearance().normals = options.normals
                entry.appearance().smooth = options.smooth

    if options.view:
        render_models(models, options.fast, options.simple, options.debug)

if __name__ == '__main__':
    parsed_options = parse_args()

    if parsed_options.debug:
        vrml_export.debug_enabled = True
        vrml_export_kicad.debug_enabled = True
        vrml_import.debug_enabled = True
        x3d_import.debug_enabled = True
        x3d_export.debug_enabled = True

    if parsed_options.view:
        from wrlconv import helpers
        from wrlconv import render_ogl41

    main(parsed_options)
