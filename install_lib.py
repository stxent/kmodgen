#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# install_lib.py
# Copyright (C) 2025 xent
# Project is distributed under the terms of the GNU General Public License v3.0

import argparse
import hashlib
import os
import re
import shutil

def list_files(path):
    output = {}
    for root, _, files in os.walk(path):
        for filename in files:
            extension = os.path.splitext(filename)[1]
            if extension == '.kicad_mod':
                entry_path = os.path.join(root, filename)
                with open(entry_path, 'rb') as file:
                    entry_data = file.read()
                entry_data_processed = re.sub('[(]tedit ([0-9a-fA-F]+)[)]', '(tedit FFFFFFFF)',
                                              entry_data.decode())
                digest = hashlib.md5()
                digest.update(entry_data_processed.encode())
                entry_hash = digest.hexdigest()
                output[filename] = (entry_path, entry_hash)
            elif extension in ('.wrl', '.x3d', '.mod'):
                entry_path = os.path.join(root, filename)
                with open(entry_path, 'rb') as file:
                    entry_data = file.read()
                digest = hashlib.md5()
                digest.update(entry_data)
                entry_hash = digest.hexdigest()
                output[filename] = (entry_path, entry_hash)
    return output

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-a', dest='apply', help='apply detected changes',
                        default=False, action='store_true')
    parser.add_argument('-d', dest='destination', help='destination folder',
                        default=None, type=str)
    parser.add_argument('-s', dest='source', help='source folder',
                        default=None, type=str)
    parser.add_argument(dest='files', nargs='*')

    return parser.parse_args()

if __name__ == '__main__':
    parsed_options = parse_args()

    if parsed_options.destination is None or parsed_options.source is None:
        raise ValueError()
    src_list = list_files(parsed_options.source)
    dst_list = list_files(parsed_options.destination)
    update_list = []
    for key in src_list:
        if key in dst_list and src_list[key][1] != dst_list[key][1]:
            update_list.append((src_list[key][0], dst_list[key][0]))
            print(f'Hash changed for {key}')
        if key not in dst_list:
            relative_path = os.path.relpath(src_list[key][0], parsed_options.source)
            update_list.append((src_list[key][0],
                                os.path.join(parsed_options.destination, relative_path)))
            print(f'New entry {key}')

    if parsed_options.apply:
        print('Installing files...')
        for entry in update_list:
            try:
                shutil.copyfile(entry[0], entry[1])
                print(f'File {os.path.basename(entry[0])} updated')
            except FileNotFoundError:
                print(f'File not found: {entry[0]}')
            except PermissionError:
                print(f'File permission error: {entry[1]}')
