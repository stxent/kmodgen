#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# archive_parts.py
# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import exporter_kicad

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='library', help='add footprints to a specified library',
                        default=None)
    parser.add_argument(dest='files', nargs='*')
    options = parser.parse_args()

    parts = []
    for filename in options.files:
        parts.append(open(filename, 'rb').read().decode('utf-8'))
    library_data = exporter_kicad.Converter.archive(parts)

    if options.library is not None:
        open(options.library, 'wb').write(library_data.encode('utf-8'))
    else:
        print(library_data)

if __name__ == '__main__':
    main()
