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

def list_entries(files):
    for filename in files:
        description = json.loads(open(filename, 'rb').read())
        if 'parts' not in description:
            raise KeyError()
        for part in description['parts']:
            if 'title' not in part or 'package' not in part or 'type' not in part['package']:
                raise KeyError()
            print(part['package']['type'] + ' ' + part['title'])

def list_footprints():
    builders = [entry[1] for entry in inspect.getmembers(sys.modules['footprints'])
        if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('footprints.')]
    types = []
    for entry in builders:
        types.extend(entry.__dict__['types'])

    for entry in types:
        print(entry.__name__)

def list_models():
    builders = [entry[1] for entry in inspect.getmembers(sys.modules['packages'])
        if inspect.ismodule(entry[1]) and entry[1].__name__.startswith('packages.')]
    types = []
    for entry in builders:
        types.extend(entry.__dict__['types'])

    for entry in types:
        print(entry.__name__)

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', dest='footprints', help='print available footprints',
                        default=False, action='store_true')
    parser.add_argument('-m', dest='models', help='print available models',
                        default=False, action='store_true')
    parser.add_argument(dest='files', nargs='*')

    return parser.parse_args()

if __name__ == '__main__':
    parsed_options = parse_args()

    if parsed_options.models and parsed_options.footprints:
        raise ValueError()
    if (parsed_options.models or parsed_options.footprints) and len(parsed_options.files) > 0:
        raise ValueError()

    if parsed_options.footprints:
        from footprints import *
        list_footprints()
    elif parsed_options.models:
        from packages import *
        list_models()
    else:
        list_entries(parsed_options.files)
