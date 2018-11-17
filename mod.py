#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# mod.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import inspect
import json
import numpy
import os
import re
import sys

from wrlconv import model
from wrlconv import vrml_export
from wrlconv import vrml_export_kicad
from wrlconv import vrml_import
from wrlconv import x3d_export
from wrlconv import x3d_import

from packages import *

builders = [entry[1] for entry in inspect.getmembers(sys.modules['packages'])
        if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('packages.')]
types = []
[types.extend(entry.__dict__['types']) for entry in builders]

def loadMaterials(entries):
    def decodeMaterial(desc, title):
        material = model.Material()
        material.color.ident = title.capitalize()
        if 'shininess' in desc:
            material.color.shininess = float(desc['shininess'])
        if 'transparency' in desc:
            material.color.transparency = float(desc['transparency'])
        if 'diffuse' in desc:
            material.color.diffuse = numpy.array(desc['diffuse'])
        if 'specular' in desc:
            material.color.specular = numpy.array(desc['specular'])
        if 'emissive' in desc:
            material.color.emissive = numpy.array(desc['emissive'])
        if 'ambient' in desc:
            material.color.ambient = numpy.array(desc['ambient'])
        return material

    materials = {}
    [materials.update({entry.capitalize(): decodeMaterial(entries[entry], entry)}) for entry in entries.keys()]
    return materials

def loadTemplates(entries, path):
    templates = []
    for entry in entries:
        scriptPath = path + '/' + entry
        extension = os.path.splitext(scriptPath)[1][1:].lower()
        if extension == 'wrl':
            templates.extend(vrml_import.load(scriptPath))
        elif extension == 'x3d':
            templates.extend(x3d_import.load(scriptPath))
    return templates

parser = argparse.ArgumentParser()
parser.add_argument('-d', dest='debug', help='show debug information', default=False, action='store_true')
parser.add_argument('-f', dest='pattern', help='filter parts by name', default='.*')
parser.add_argument('-l', dest='library', help='add footprints to a specified library', default=None)
parser.add_argument('-o', dest='output', help='write models to a specified directory', default='')
parser.add_argument('-v', dest='view', help='render models', default=False, action='store_true')
parser.add_argument('--fast', dest='fast', help='disable visual effects', default=False, action='store_true')
parser.add_argument('--no-grid', dest='simple', help='disable grid', default=False, action='store_true')
parser.add_argument('--normals', dest='normals', help='show normals', default=False, action='store_true')
parser.add_argument('--smooth', dest='smooth', help='use smooth shading', default=False, action='store_true')
parser.add_argument('--vrml', dest='vrml', help='use VRML model format', default=False, action='store_true')
parser.add_argument(dest='files', nargs='*')
options = parser.parse_args()

if options.debug:
    vrml_export.debugEnabled = True
    vrml_export_kicad.debugEnabled = True
    vrml_import.debugEnabled = True
    x3d_import.debugEnabled = True
    x3d_export.debugEnabled = True

models = []
pattern = re.compile(options.pattern, re.S)

for filename in options.files:
    desc = json.load(open(filename, 'rb'))

    materials = loadMaterials(desc['materials']) if 'materials' in desc else {}
    templates = loadTemplates(desc['templates'], os.path.dirname(filename)) if 'templates' in desc else []

    for part in filter(lambda x: pattern.search(x['title']) is not None, desc['parts']):
        package = next(filter(lambda x: x.__name__ == part['package']['type'], types), None)
        if package is not None:
            models.append((package().generate(materials, templates, part), part['title']))

if options.output != '':
    if options.library is not None:
        libraryPath = os.path.join(options.output, options.library)
    else:
        libraryPath = options.output
    if not os.path.exists(libraryPath):
        os.makedirs(libraryPath)

    extension = '.wrl' if options.vrml else '.x3d'
    exportFunc = vrml_export_kicad.store if options.vrml else x3d_export.store
    for group in models:
        exportFunc(group[0], os.path.join(libraryPath, group[1] + extension))
        if options.debug:
            print('Model {:s}:{:s} was exported'.format(group[1], extension))

if options.normals or options.smooth:
    for group in models:
        for entry in group[0]:
            entry.appearance().normals = options.normals
            entry.appearance().smooth = options.smooth

if options.view:
    from wrlconv import helpers
    from wrlconv import render_ogl41

    if options.debug:
        render_ogl41.debugEnabled = True

    effects = {} if options.fast else {'antialiasing': 4}
    helperObjects = [] if options.simple else helpers.createGrid()
    exportList = []
    [exportList.extend(entry[0]) for entry in models]
    render = render_ogl41.Render(helperObjects + exportList, effects)
