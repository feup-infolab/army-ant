#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import logging, string, asyncio, pymongo, re
from aiogremlin import Cluster
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from nltk import word_tokenize
from nltk.corpus import stopwords, wordnet as wn
from army_ant.util import load_gremlin_script
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Index(object):
    @staticmethod
    def factory(reader, index_location, index_type, loop):
        if index_type == 'gow':
            return GraphOfWord(reader, index_location, loop)
        elif index_type == 'goe':
            return GraphOfEntity(reader, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    def open(index_location, index_type, loop):
        if index_type == 'gow':
            return GraphOfWord(None, index_location, loop)
        elif index_type == 'goe':
            return GraphOfEntity(None, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    def __init__(self, reader, index_location, loop):
        self.reader = reader
        self.index_location = index_location
        self.loop = loop

    def analyze(self, text):
        tokens = word_tokenize(text.lower())
        tokens = [token for token in tokens if token not in stopwords.words('english') and not token[0] in string.punctuation]
        return tokens

    # TODO cache results without aiocache (has logging issue; cannot disable)
    async def get_or_create_vertex(self, vertex_name, data=None):
        result_set = await self.client.submit(
            load_gremlin_script('get_or_create_vertex'),
            {'vertexName': vertex_name, 'data': data})
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def get_or_create_edge(self, source_vertex, target_vertex, edge_type='before', data=None):
        result_set = await self.client.submit(
            load_gremlin_script('get_or_create_edge'), {
                'sourceID': source_vertex.id,
                'targetID': target_vertex.id,
                'edgeType': edge_type,
                'data': data
            })
        results = await result_set.all()
        return results[0] if len (results) > 0 else None

    async def index(self):
        raise ArmyAntException("Index not implemented for %s" % self.__class__.__name__)

    async def search(self, query):
        raise ArmyAntException("Search not implemented for %s" % self.__class__.__name__)

class GraphOfWord(Index):
    def __init__(self, reader, index_location, loop, window_size=3):
        super().__init__(reader, index_location, loop)
        self.window_size = 3
    
    async def index(self):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_location])
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            tokens = self.analyze(doc.text)

            for i in range(len(tokens)-self.window_size):
                for j in range(1, self.window_size + 1):
                    logger.debug("%s -> %s" % (tokens[i], tokens[i+j]))
                    source_vertex = await self.get_or_create_vertex(tokens[i])
                    target_vertex = await self.get_or_create_vertex(tokens[i+j])
                    edge = await self.get_or_create_edge(
                        source_vertex, target_vertex, data={'doc_id': doc.doc_id})

            yield doc

        await self.cluster.close()

    async def search(self, query):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_location])
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

        result_set = await self.client.submit(
            load_gremlin_script('graph_of_word_query'), {
                'queryTokens': query_tokens
            })
        results = await result_set.all()
        await self.cluster.close()

        return results

class GraphOfEntity(Index):
    async def index(self):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_location])
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            # Load entities and relations (knowledge base)
            for (e1, rel, e2) in doc.triples:
                logger.debug("%s -[%s]-> %s" % (e1, rel, e2))
                source_vertex = await self.get_or_create_vertex(e1, data={'type': 'entity'})
                target_vertex = await self.get_or_create_vertex(e2, data={'type': 'entity'})
                edge = await self.get_or_create_edge(source_vertex, target_vertex, edge_type=rel)

            tokens = self.analyze(doc.text)

            for i in range(len(tokens)-1):
                # Load words, linking by sequential co-occurrence
                logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i+1]))
                source_vertex = await self.get_or_create_vertex(tokens[i], data={'type': 'term'})
                target_vertex = await self.get_or_create_vertex(tokens[i+1], data={'type': 'term'})
                edge = await self.get_or_create_edge(source_vertex, target_vertex, data={'doc_id': doc.doc_id})

                # Load word synonyms, linking to original term

                source_syns = set([ss.name().split('.')[0] for ss in wn.synsets(tokens[i])])
                source_syns = source_syns.difference(tokens[i])

                target_syns = set([ss.name().split('.')[0] for ss in wn.synsets(tokens[i+1])])
                target_syns = target_syns.difference(tokens[i+1])

                for syn in source_syns:
                    logger.debug("%s -[synonym]-> %s" % (tokens[i], syn))
                    syn_vertex = await self.get_or_create_vertex(syn, data={'type': 'term'})
                    edge = await self.get_or_create_edge(source_vertex, syn_vertex)

                for syn in target_syns:
                    logger.debug("%s -[synonym]-> %s" % (tokens[i+1], syn))
                    syn_vertex = await self.get_or_create_vertex(syn, data={'type': 'term'})
                    edge = await self.get_or_create_edge(target_vertex, syn_vertex)

                # Load word-entity occurrence

                for (e1, _, e2) in doc.triples:
                    if len(re.findall(r'\b' + tokens[i] + r'\b', e1.lower())) > 0:
                        logger.debug("%s -[contained_in]-> %s" % (tokens[i], e1))
                        e1_vertex = await self.get_or_create_vertex(e1, data={'type': 'entity'})
                        edge = await self.get_or_create_edge(source_vertex, e1_vertex)

                    if len(re.findall(r'\b' + tokens[i+1] + r'\b', e2.lower())) > 0:
                        logger.debug("%s -[contained_in]-> %s" % (tokens[i+1], e2))
                        e2_vertex = await self.get_or_create_vertex(e2, data={'type': 'entity'})
                        edge = await self.get_or_create_edge(source_vertex, e2_vertex)

            yield doc

        await self.cluster.close()

    async def search(self, query):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_location])
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

        result_set = await self.client.submit(
            load_gremlin_script('graph_of_entity_query'), {
                'queryTokens': query_tokens
            })
        results = await result_set.all()
        await self.cluster.close()

        return results
