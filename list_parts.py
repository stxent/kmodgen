#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# list_parts.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import inspect
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument('-f', dest='footprints', help='print available footprints', default=False, action='store_true')
parser.add_argument('-m', dest='models', help='print available models', default=False, action='store_true')
parser.add_argument(dest='files', nargs='*')
options = parser.parse_args()

if options.models and options.footprints:
    raise Exception()
if (options.models or options.footprints) and len(options.files) > 0:
    raise Exception()

if options.footprints:
    from footprints import *

    builders = [entry[1] for entry in inspect.getmembers(sys.modules['footprints'])
            if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('footprints.')]
    types = []
    [types.extend(entry.__dict__['types']) for entry in builders]

    for entry in types:
        print(entry.__name__)
elif options.models:
    from packages import *

    builders = [entry[1] for entry in inspect.getmembers(sys.modules['packages'])
            if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('packages.')]
    types = []
    [types.extend(entry.__dict__['types']) for entry in builders]

    for entry in types:
        print(entry.__name__)
else:
    for filename in options.files:
        description = json.loads(open(filename, 'rb').read())
        if 'parts' not in description:
            raise Exception()
        for part in description['parts']:
            if 'title' not in part or 'package' not in part or 'type' not in part['package']:
                raise Exception()
            print(part['package']['type'] + ' ' + part['title'])
