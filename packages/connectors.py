#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# connectors.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

from packages import generic


class IPX(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(IPX.PIVOT_NONE)


class MemoryCard(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(IPX.PIVOT_NONE)


class SMA(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(IPX.PIVOT_NONE)


class USB(generic.GenericModelFilter):
    def __init__(self):
        super().__init__(IPX.PIVOT_NONE)


types = [
    IPX,
    MemoryCard,
    SMA,
    USB
]
