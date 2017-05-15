#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# test.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-15

import logging

from army_ant.reader import INEXReader

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

def test_inexreader():
    for item in INEXReader("/media/backups/Datasets/INEX 2009/dataset/sample.tar.bz2"):
        print(item)

if __name__ == '__main__':
    # This is used during development to test individual methods.
    test_inexreader()
