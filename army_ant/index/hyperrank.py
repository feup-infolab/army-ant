#!/usr/bin/env python
#
# hyperrank.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-03-15

import logging
import random

import keras
import numpy as np
import tensorflow as tf

from army_ant.index import Index, Result, ResultSet

logger = logging.getLogger(__name__)

# TODO implement as a different ranking function over HGoE
class HyperRank(Index):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.term_dict = {}
        self.entity_dict = {}

    # TODO improve actual keyword extraction
    def keyword_extraction(self, doc, k=10):
        terms = self.analyze(doc.text)
        if len(terms) < 1:
            return []
        return np.random.choice(terms, size=k)

    # TODO improve actual entity extraction
    def entity_extraction(self, doc, k=10):
        if len(doc.entities) < 1:
            return []
        return np.random.choice(doc.entities, size=k)

    async def index(self, features_location=None):
        k1 = 15
        k2 = 5

        #saver = tf.train.Saver()

        with tf.Session() as sess:
            indices = []
            values = []
            count = 0

            for doc in self.reader:
                doc_indices = []

                T = self.keyword_extraction(doc, k=k1)
                E = self.entity_extraction(doc, k=k2)

                for t in T:
                    idx = self.term_dict.get(t)
                    if idx is None:
                        idx = self.term_dict[t] = len(self.term_dict) + len(self.entity_dict)
                    doc_indices.append(idx)

                for e in E:
                    entity_label = e.label.lower()
                    idx = self.entity_dict.get(entity_label)
                    if idx is None:
                        idx = self.entity_dict[entity_label] = len(self.term_dict) + len(self.entity_dict)
                    doc_indices.append(idx)

                indices.append(doc_indices)
                values.append(1)

                count +=1
                if count % 100 == 0:
                    logger.info("%d documents processed" % count)

                yield doc

                if count > 200: break

            size = len(self.term_dict) + len(self.entity_dict)
            k = k1 + k2
            shape = [size] * k
            H = tf.sparse.SparseTensor(indices=indices, values=values, dense_shape=shape)
            M = tf.sparse.reshape(H, [size, size ** (k - 1)])
            print(M.eval(session=sess))
            #saver.save(sess, os.path.join(self.index_location, "hypergraph.ckpt"))

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        return ResultSet()
