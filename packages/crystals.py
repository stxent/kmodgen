#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# crystals.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from packages import generic


class CrystalSMD(generic.GenericModelFilter):
    def __init__(self):
        generic.GenericModelFilter.__init__(self, CrystalSMD.PIVOT_BOUNDING_BOX_CENTER)


types = [
        CrystalSMD
]
