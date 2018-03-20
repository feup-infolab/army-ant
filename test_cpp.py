#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_cpp.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-06

import sys, os

sys.path.append('external/cpp-impl/cmake-build-debug/src')
from army_ant.reader import Document, Entity, INEXDirectoryReader;
from army_ant_cpp import HypergraphOfEntity;

hg = HypergraphOfEntity("/tmp/hgoe++")

# hg.index(Document(doc_id="1", entity="História1",
#                   text="Era uma vez uma coisa que eu queria tokenizer, mas convenientemente."))
# hg.index(Document(doc_id="2", entity="História2", triples=[(Entity("a", "http://a"), "b", Entity("c", "http://c")),
#                                                            (Entity("c", "http://c"), "e", Entity("f", "http://f"))]))
# hg.index(
#     Document(doc_id="3", entity="História3",
#              text="Era uma vez uma coisa que eu queria tokenizer, mas convenientemente.",
#              triples=[(Entity("a", "http://a"), "b", Entity("c", "http://c")),
#                       (Entity("c", "http://c"), "e", Entity("f", "http://f"))]))

print("===> Preparing reader")
reader = INEXDirectoryReader("/media/hdd0/datasets/inex-2009-3t-nl/corpus", use_memory=True)

print("===> Indexing")
for doc in reader:
   hg.index(doc)

hg.post_processing()

hg.save()

#hg.load()
#for result in hg.search("music", 0, 10):
#    print(result)