#!/usr/bin/env python
#
# hyperrank.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-03-15

import logging
import random
import tensorflow as tf

from army_ant.index import Index, Result, ResultSet

logger = logging.getLogger(__name__)


class HyperRank(Index):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)

    # TODO improve actual keyword extraction
    def keyword_extraction(self, doc, k=10):
        return random.choices(self.analyze(doc.text), k=k)

    # TODO improve actual entity extraction
    def entity_extraction(self, doc, k=10):
        return random.choices(doc.entities, k=10)

    async def index(self, features_location=None):
        #H = tf.placeholder()
        for doc in self.reader:
            T = self.keyword_extraction(doc)
            E = self.entity_extraction(doc)
            print(T)
            print(E)
            yield doc

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        return ResultSet()
