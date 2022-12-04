#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# opto.py
# Copyright (C) 2022 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from packages import generic


class OptoPLCC(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(OptoPLCC.PIVOT_BOUNDING_BOX_CENTER)


types = [OptoPLCC]
