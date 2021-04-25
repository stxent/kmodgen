#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# switches.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from packages import generic


class Button(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(Button.PIVOT_BOUNDING_BOX_CENTER)


types = [Button]
