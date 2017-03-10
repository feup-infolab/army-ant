#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import logging, string, asyncio
from goblin import driver
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from nltk import word_tokenize
from nltk.corpus import stopwords
from army_ant.gremlin import load_gremlin_script
from army_ant.exception import ArmyAntException

THREAD_POOL = ThreadPoolExecutor(10)

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

class GraphOfWord(Index):
    def __init__(self, index_path, index_type):
        super(GraphOfWord, self).__init__(index_path, index_type)
        #self.client = gremlinrestclient.GremlinRestClient()

    @lru_cache(maxsize=500)
    async def get_or_create_vertex(self, loop, vertex_name, data=None):
        logging.debug(vertex_name)
        #resp = self.client.execute(
            #load_gremlin_script('get_or_create_vertex'),
            #bindings={'vertex_name': vertex_name})
        conn = await driver.Connection.open('ws://localhost:8182/gremlin', loop)
        async with conn:
            print(conn.submit(
                gremlin=load_gremlin_script('get_or_create_vertex'),
                bindings={'vertex_name': vertex_name}))

        #logging.debug(resp)
        #return resp.data

    def create_edge(self, source_vertex, target_vertex, edge_type='before', data=None):
        pass

    def index(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.index_async(loop))
        loop.close()

    #async def index_async(self, loop):
        #script = "g.addV('developer').property(k1, v1)"
        #bindings = {'k1': 'name', 'v1': 'Leif'}
        #conn = await driver.Connection.open(
            #'ws://localhost:8182/gremlin', loop)
        #async with conn:
            #resp = await conn.submit(gremlin=script, bindings=bindings)
            #async for msg in resp:
                #print(msg)

    async def index_async(self, loop):
        for doc in self.reader:
            tokens = word_tokenize(doc.text.lower())
            tokens = [token for token in tokens if token not in stopwords.words('english') and not token[0] in string.punctuation]

            for i in range(len(tokens)-1):
                #source_vertex = await self.get_or_create_vertex(tokens[i])
                #target_vertex = await self.get_or_create_vertex(tokens[i+1])
                futures = [
                    loop.run_in_executor(THREAD_POOL, self.get_or_create_vertex, tokens[i]),
                    loop.run_in_executor(THREAD_POOL, self.get_or_create_vertex, tokens[i+1])
                ]
                await asyncio.wait(futures)
                for future in futures:
                    print(future.result())
                #self.create_edge(source_vertex, target_vertex, data={'doc_id': doc.doc_id})

class GraphOfEntity(Index):
    pass
