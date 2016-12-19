#!/usr/bin/env python
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
from wrlconv import vrml_export_kicad
from wrlconv import vrml_import
from wrlconv import x3d_import
from wrlconv import x3d_export

from packages import *

builders = [entry[1] for entry in inspect.getmembers(sys.modules["packages"])
        if inspect.ismodule(entry[1]) and entry[1].__name__.startswith("packages.")]
types = []
[types.extend(entry.__dict__["types"]) for entry in builders]

def loadMaterials(path):
    def decodeMaterial(description):
        material = model.Material()
        material.color.ident = description["title"]
        if "shininess" in description.keys():
            material.color.shininess = float(description["shininess"])
        if "transparency" in description.keys():
            material.color.transparency = float(description["transparency"])
        if "diffuse" in description.keys():
            material.color.diffuse = numpy.array(description["diffuse"])
        if "specular" in description.keys():
            material.color.specular = numpy.array(description["specular"])
        if "emissive" in description.keys():
            material.color.emissive = numpy.array(description["emissive"])
        if "ambient" in description.keys():
            material.color.ambient = numpy.array(description["ambient"])
        return material

    materials = {}
    content = json.loads(open(path, "rb").read())
    if "materials" in content.keys():
        for description in content["materials"]:
            if "title" not in description.keys():
                raise Exception()
            materials[description["title"]] = decodeMaterial(description)

    return materials

parser = argparse.ArgumentParser()
parser.add_argument("-d", dest="debug", help="show debug information", default=False, action="store_true")
parser.add_argument("-f", dest="format", help="output file format", default="x3d")
parser.add_argument("-i", dest="input", help="input file with part descriptions", default="")
parser.add_argument("-m", dest="materials", help="file with materials", default="")
parser.add_argument("-o", dest="output", help="write models to specified directory", default="")
parser.add_argument("-v", dest="view", help="render models", default=False, action="store_true")
parser.add_argument("--fast", dest="fast", help="disable visual effects", default=False, action="store_true")
parser.add_argument("--normals", dest="normals", help="show normals", default=False, action="store_true")
parser.add_argument("--smooth", dest="smooth", help="use smooth shading", default=False, action="store_true")
parser.add_argument(dest="files", nargs="*")
options = parser.parse_args()

if options.debug:
    vrml_export.debugEnabled = True
    vrml_export_kicad.debugEnabled = True
    vrml_import.debugEnabled = True
    x3d_import.debugEnabled = True
    x3d_export.debugEnabled = True

for entry in builders:
    entry.debugNormals = options.normals
    entry.debugSmoothShading = options.smooth

templates = []
for filename in options.files:
    extension = os.path.splitext(filename)[1][1:].lower()
    if extension == "wrl":
        templates.extend(vrml_import.load(filename))
    elif extension == "x3d":
        templates.extend(x3d_import.load(filename))

materials = loadMaterials(options.materials) if options.materials != "" else {} 
models = []

if options.input != "":
    content = json.loads(open(options.input, "rb").read())
    if "parts" not in content.keys():
        raise Exception()

    for descriptor in content["parts"]:
        for package in types:
            if package.__name__ == descriptor["package"]["type"]:
                models.append((package.build(materials, templates, descriptor), descriptor["title"].lower()))
                break

if options.output != "":
    outputPath = options.output
    if outputPath[-1] != '/':
        outputPath += '/'
    exportFunc = {"wrl": vrml_export_kicad.store, "x3d": x3d_export.store}[options.format] 
    for entry in models:
        exportFunc(entry[0], outputPath + entry[1] + "." + options.format)
        print("Model %s.%s was exported" % (entry[1], options.format))

if options.view:
    from wrlconv import helpers
    from wrlconv import render_ogl41
    
    if options.debug:
        render_ogl41.debugEnabled = True
    
    effects = {} if options.fast else {"antialiasing": 4}
    helperObjects = helpers.createGrid()
    exportList = []
    [exportList.extend(entry[0]) for entry in models]
    render = render_ogl41.Render(helperObjects + exportList, effects)
