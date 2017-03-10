#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# gremlin.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-10

import os

def load_gremlin_script(script_name):
    with open(os.path.join('gremlin', script_name + '.groovy'), 'r') as f:
        return f.read()
