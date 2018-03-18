#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# __init__.py
# Copyright (C) 2016 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import os

__all__ = list(map(lambda x: x[:-3], filter(lambda x: x.endswith(".py") and x != "__init__.py",
        os.listdir(os.path.dirname(__file__)))))
