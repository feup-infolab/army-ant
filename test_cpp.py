#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_cpp.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-06

import sys, os

sys.path.append('external/cpp-impl/cmake-build-debug/src')
from army_ant.reader import Document;
from army_ant_cpp import HypergraphOfEntity;

hg = HypergraphOfEntity()
hg.index(Document(doc_id="1", entity="História1",
                  text="Era uma vez uma coisa que eu queria tokenizer, mas convenientemente."))
hg.index(Document(doc_id="2", entity="História2", triples=[("a", "b", "c"), ("c", "e", "f")]))
hg.index(
    Document(doc_id="3", entity="História3", text="Era uma vez uma coisa que eu queria tokenizer, mas convenientemente.",
             triples=[("a", "b", "c"), ("c", "e", "f")]))
