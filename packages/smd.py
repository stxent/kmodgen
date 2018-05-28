#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# smd.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from packages import generic


class Chip(generic.GenericModelFilter):
    def __init__(self):
        generic.GenericModelFilter.__init__(self, Chip.PIVOT_BOUNDING_BOX_CENTER)


class SOT223(generic.GenericModelFilter):
    def __init__(self):
        generic.GenericModelFilter.__init__(self, SOT223.PIVOT_BOUNDING_BOX_CENTER)


class SOT23(generic.GenericModelFilter):
    def __init__(self):
        generic.GenericModelFilter.__init__(self, SOT23.PIVOT_BOUNDING_BOX_CENTER)


types = [
        Chip,
        SOT223,
        SOT23
]
