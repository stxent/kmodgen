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
import sys

from wrlconv import model
from wrlconv import vrml_export
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
        if 'shininess' in desc.keys():
            material.color.shininess = float(desc['shininess'])
        if 'transparency' in desc.keys():
            material.color.transparency = float(desc['transparency'])
        if 'diffuse' in desc.keys():
            material.color.diffuse = numpy.array(desc['diffuse'])
        if 'specular' in desc.keys():
            material.color.specular = numpy.array(desc['specular'])
        if 'emissive' in desc.keys():
            material.color.emissive = numpy.array(desc['emissive'])
        if 'ambient' in desc.keys():
            material.color.ambient = numpy.array(desc['ambient'])
        return material

    materials = {}
    [materials.update({entry.capitalize(): decodeMaterial(entries[entry], entry)}) for entry in entries.keys()]
    return materials

def loadTemplates(entries):
    templates = []
    scriptDir = os.path.dirname(os.path.realpath(__file__)) + "/descriptions/"
    for entry in entries:
        scriptPath = scriptDir + entry
        extension = os.path.splitext(scriptPath)[1][1:].lower()
        if extension == 'wrl':
            templates.extend(vrml_import.load(scriptPath))
        elif extension == 'x3d':
            templates.extend(x3d_import.load(scriptPath))
    return templates

parser = argparse.ArgumentParser()
parser.add_argument('-d', dest='debug', help='show debug information', default=False, action='store_true')
parser.add_argument("-f", dest="format", help="output file format", default="x3d")
parser.add_argument("-i", dest="input", help="input file with part descriptions", default="")
parser.add_argument('-o', dest='output', help='write models to a specified directory', default='')
parser.add_argument('-v', dest='view', help='render models', default=False, action='store_true')
parser.add_argument('--fast', dest='fast', help='disable visual effects', default=False, action='store_true')
parser.add_argument('--no-grid', dest='simple', help='disable grid', default=False, action='store_true')
parser.add_argument('--normals', dest='normals', help='show normals', default=False, action='store_true')
parser.add_argument('--smooth', dest='smooth', help='use smooth shading', default=False, action='store_true')
options = parser.parse_args()

if options.debug:
    vrml_export.debugEnabled = True
    vrml_export_kicad.debugEnabled = True
    vrml_import.debugEnabled = True
    x3d_import.debugEnabled = True
    x3d_export.debugEnabled = True

models = []

if options.input != "":
    description = json.loads(open(options.input, "rb").read())
    if "library" not in description.keys() and "parts" not in description.keys():
        raise Exception()
    materials = loadMaterials(description["materials"]) if "materials" in description.keys() else {}
    templates = loadTemplates(description["templates"]) if "templates" in description.keys() else []

    for descriptor in description["parts"]:
        for package in types:
            if package.__name__ == descriptor["package"]["type"]:
                models.append((package.build(materials, templates, descriptor), descriptor["title"].lower()))
                break

if options.output != '':
    libraryPath = options.output
    if libraryPath[-1] != '/':
        libraryPath += '/'
    libraryPath += description["library"] + "/"
    if not os.path.exists(libraryPath):
        os.makedirs(libraryPath)

    exportFunc = {"wrl": vrml_export.store, "x3d": x3d_export.store}[options.format]
    for group in models:
        exportFunc(group[0], libraryPath + group[1] + "." + options.format)
        if options.debug:
            print("Model %s.%s was exported" % (group[1], options.format))

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
