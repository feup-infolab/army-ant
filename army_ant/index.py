#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import logging, string, asyncio
from aiogremlin import Cluster
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from nltk import word_tokenize
from nltk.corpus import stopwords
from army_ant.util import load_gremlin_script
from army_ant.exception import ArmyAntException

class Index(object):
    @staticmethod
    def factory(reader, index_path, index_type):
        if index_type == 'gow':
            return GraphOfWord(reader, index_path)
        elif index_type == 'goe':
            return GraphOfEntity(reader, index_path)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    def __init__(self, reader, index_path):
        self.reader = reader
        self.index_path = index_path

    def index(self):
        raise ArmyAntException("Graph index not implemented")

    def query(self, query):
        raise ArmyAntException("Graph query not implemented")

class GraphOfWord(Index):
    def __init__(self, index_path, index_type, window_size=3):
        super(GraphOfWord, self).__init__(index_path, index_type)
        self.window_size = 3
        self.logger = logging.getLogger(__name__)
    
    # TODO cache results without aiocache (has logging issue; cannot disable)
    async def get_or_create_vertex(self, vertex_name, data=None):
        result_set = await self.client.submit(
            load_gremlin_script('get_or_create_vertex'),
            {'vertex_name': vertex_name, 'data': data})
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def get_or_create_edge(self, source_vertex, target_vertex, edge_type='before', data=None):
        result_set = await self.client.submit(
            load_gremlin_script('get_or_create_edge'), {
                'source_id': source_vertex.id,
                'target_id': target_vertex.id,
                'edge_type': edge_type,
                'data': data
            })
        results = await result_set.all()
        return results[0] if len (results) > 0 else None

    def index(self):
        self.loop = asyncio.get_event_loop()
        try:
            return self.loop.run_until_complete(self.index_async())
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    def query(self, query):
        pass

    async def index_async(self):
        self.cluster = await Cluster.open(self.loop)
        self.client = await self.cluster.connect()

        for doc in self.reader:
            tokens = word_tokenize(doc.text.lower())
            tokens = [token for token in tokens if token not in stopwords.words('english') and not token[0] in string.punctuation]
            # TODO generate sliding windows of size 3

            self.logger.info("Indexing %s" % doc.doc_id)
            self.logger.debug(doc.text)

            for i in range(len(tokens)-self.window_size):
                for j in range(1, self.window_size + 1):
                    self.logger.debug("%s -> %s" % (tokens[i], tokens[i+j]))
                    source_vertex = await self.get_or_create_vertex(tokens[i])
                    target_vertex = await self.get_or_create_vertex(tokens[i+j])
                    edge = await self.get_or_create_edge(
                        source_vertex, target_vertex, data={'doc_id': doc.doc_id})

        await self.cluster.close()

class GraphOfEntity(Index):
    pass
