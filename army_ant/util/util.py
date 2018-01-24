#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# util.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import os, logging, hashlib, zipfile
from bs4 import BeautifulSoup

def html_to_text(html):
    soup = BeautifulSoup(html, "html5lib")

    for script in soup(["script", "style"]):
        script.extract()

    text = ''.join(soup.strings)

    lines = [line.strip() for line in text.splitlines()]
    chunks = [phrase.strip() for line in lines for phrase in line.split(' ')]
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text#.encode('utf-8')

def load_gremlin_script(script_name):
    with open(os.path.join('gremlin', script_name + '.groovy'), 'r') as f:
        return f.read()

def load_sql_script(script_name):
    with open(os.path.join('sql', script_name + '.sql'), 'r') as f:
        return f.read()

def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_first(lst, default=None):
    return next(iter(lst or []), default)

def zipdir(path, ziph):
    pwd = os.getcwd()
    os.chdir(os.path.dirname(path))
    for root, dirs, files in os.walk(os.path.basename(path)):
        for file in files:
            ziph.write(os.path.join(root, file))
    os.chdir(pwd)

def set_dict_defaults(d, defaults):
    for k, v in defaults.items():
        if isinstance(v, dict):
            set_dict_defaults(d.setdefault(k, {}), v)
        else:
            d.setdefault(k, v)

def safe_div(n, d):
    if d == 0: return 0
    return n / d

def ranking_params_to_params_id(ranking_params):
    if ranking_params is None or len(ranking_params) < 1: return 'no_params'
    return '-'.join([p[0] + '_' + str(p[1]) for p in ranking_params.items()])

def params_id_to_str(params_id):
    if params_id == 'no_params': return "No parameters"
    params = []
    for p in params_id.split('-'):
        params.append('%s=%s' % tuple(p.split('_', 1)))
    return '(%s)' % ', '.join(params)
