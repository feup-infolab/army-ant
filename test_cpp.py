#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_cpp.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-06

from army_ant.reader import Document;
from army_ant_cpp import HypergraphOfEntity;

hg = HypergraphOfEntity()
hg.index(Document(doc_id=1, text="Era uma vez uma coisa que eu queria tokenizer, mas convenientemente."))