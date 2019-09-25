#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# inex.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-10-10

import os


def filter_xml_files(members):
    for member in members:
        if os.path.splitext(member.name)[1] == '.xml':
            yield member


def xlink_to_page_id(xlink):
    _, filename = os.path.split(xlink)
    return os.path.splitext(filename)[0]
