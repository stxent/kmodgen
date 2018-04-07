#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# generic.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import re

def lookup(meshList, meshName):
    found = []
    for entry in meshList:
        if re.search(meshName, entry.ident, re.S) is not None:
            found.append(entry)
    return found


class GenericModelFilter:
    @staticmethod
    def build(materials, templates, descriptor):
        meshes = lookup(templates, descriptor['title'])
        return meshes if len(meshes) > 0 else None


types = [GenericModelFilter]
