#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# util.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import os, logging, hashlib
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

def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

