#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import logging, string, asyncio, pymongo, re, json, psycopg2
from aiogremlin import Cluster
from aiogremlin.gremlin_python.structure.graph import Vertex
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from nltk import word_tokenize
from nltk.corpus import stopwords, wordnet as wn
from army_ant.reader import Document
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Index(object):
    @staticmethod
    def factory(reader, index_location, index_type, loop):
        if index_type == 'gow':
            return GraphOfWord(reader, index_location, loop)
        elif index_type == 'gow-batch':
            return GraphOfWordBatch(reader, index_location, loop)
        elif index_type == 'goe':
            return GraphOfEntity(reader, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    def open(index_location, index_type, loop):
        if index_type == 'gow':
            return GraphOfWord(None, index_location, loop)
        elif index_type == 'gow-batch':
            return GraphOfWordBatch(None, index_location, loop)
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

    """Indexes the documents and yields documents to store in the database."""
    async def index(self):
        raise ArmyAntException("Index not implemented for %s" % self.__class__.__name__)

    async def search(self, query, offset, limit):
        raise ArmyAntException("Search not implemented for %s" % self.__class__.__name__)

class ServiceIndex(Index):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        index_location_parts = self.index_location.split('/')
        if len(index_location_parts) > 1:
            self.index_path = index_location_parts[1]
        else:
            self.index_path = None

        index_location_parts = index_location_parts[0].split(':')
        if len(index_location_parts) > 1:
            self.index_host = index_location_parts[0]
            self.index_port = index_location_parts[1]
        else:
            self.index_host = index_location_parts[0]
            self.index_port = 8182

class GraphOfWord(ServiceIndex):
    def __init__(self, reader, index_location, loop, window_size=3):
        super().__init__(reader, index_location, loop)
        self.window_size = 3
    
    async def index(self):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
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

    async def search(self, query, offset, limit):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

        graph = self.index_path if self.index_path else 'graph'

        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % graph)
            + load_gremlin_script('graph_of_word_query'), {
                'queryTokens': query_tokens,
                'offset': offset,
                'limit': limit
            })
        results = await result_set.one()
        await self.cluster.close()

        return results

class GraphOfWordBatch(GraphOfWord):
    def create_postgres_schema(self, conn):
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS nodes")
        c.execute("DROP TABLE IF EXISTS edges")
        c.execute("CREATE TABLE nodes (node_id BIGINT, label TEXT, attributes JSON)")
        c.execute("CREATE TABLE edges (edge_id BIGINT, label TEXT, attributes JSON, source_node_id BIGINT, target_node_id BIGINT)")
        conn.commit()

    def create_vertex_postgres(self, conn, vertex_id, label, attributes):
        c = conn.cursor()
        properties = {}
        for k, v in attributes.items():
            properties[k] = [{ 'id': self.next_property_id, 'value': v }]
            self.next_property_id += 1
        c.execute("INSERT INTO nodes VALUES (%s, %s, %s)", (vertex_id, label, json.dumps(properties)))

    def create_edge_postgres(self, conn, edge_id, label, attributes, source_vertex_id, target_vertex_id):
        c = conn.cursor()
        c.execute("INSERT INTO edges VALUES (%s, %s, %s, %s, %s)", (edge_id, label, json.dumps(attributes), source_vertex_id, target_vertex_id))

    def load_to_postgres(self, conn, doc_id, tokens):
        for i in range(len(tokens)-self.window_size):
            for j in range(1, self.window_size + 1):
                if tokens[i] in self.vertex_cache:
                    source_vertex_id = self.vertex_cache[tokens[i]]
                else:
                    source_vertex_id = self.next_vertex_id
                    self.vertex_cache[tokens[i]] = source_vertex_id
                    self.next_vertex_id += 1
                    self.create_vertex_postgres(conn, source_vertex_id, 'term', { 'name': tokens[i] })

                if tokens[i+j] in self.vertex_cache:
                    target_vertex_id = self.vertex_cache[tokens[i+j]]
                else:
                    target_vertex_id = self.next_vertex_id
                    self.vertex_cache[tokens[i+j]] = target_vertex_id
                    self.next_vertex_id += 1
                    self.create_vertex_postgres(conn, target_vertex_id, 'term', { 'name': tokens[i+j] })

                logger.debug("%s (%d) -> %s (%s)" % (tokens[i], source_vertex_id, tokens[i+j], target_vertex_id))

                self.create_edge_postgres(conn, self.next_edge_id, 'in_window_of', { 'doc_id': doc_id }, source_vertex_id, target_vertex_id)
                self.next_edge_id += 1

        conn.commit()

    def postgres_to_graphson(self, conn, filename):
        logger.info("Converting PostgreSQL nodes and edges into the GraphSON format")

        with open(filename, 'w') as f:
            c = conn.cursor()
            c.execute(load_sql_script('to_graphson'))

            for row in c:
                node = { 'id': row[0], 'label': row[1] }
                if row[2]: node['properties'] = row[2]
                if row[3]: node['outE'] = row[3]
                if row[4]: node['inE'] = row[4]
                f.write(json.dumps(node) + '\n')

    async def load_to_gremlin_server(self, graphson_path):
        logger.info("Bulk loading to JanusGraph...")
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        result_set = await self.client.submit(
            load_gremlin_script('load_graphson'),
            {'graphsonPath': graphson_path, 'indexPath': self.index_path})
        results = await result_set.all()

        await self.cluster.close()

    async def index(self):
        self.next_vertex_id = 1
        self.next_edge_id = 1
        self.next_property_id = 1
        self.vertex_cache = {}

        conn = psycopg2.connect("dbname='army_ant' user='army_ant' host='localhost'")
        self.create_postgres_schema(conn)

        count = 0
        for doc in self.reader:
            count += 1
            if count > 5: break

            logger.info("Building vertex and edge records for %s" % doc.doc_id)
            logger.debug(doc.text)

            tokens = self.analyze(doc.text)
            self.load_to_postgres(conn, doc.doc_id, tokens)

            yield doc
            #break

        conn.commit()
        self.postgres_to_graphson(conn, '/tmp/gow.json')
        conn.close()

        await self.load_to_gremlin_server('/tmp/gow.json')

class GraphOfEntity(ServiceIndex):
    async def index(self):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            # Load entities and relations (knowledge base)
            for (e1, rel, e2) in doc.triples:
                logger.debug("%s -[%s]-> %s" % (e1.label, rel, e2.label))
                source_vertex = await self.get_or_create_vertex(e1.label, data={'doc_id': doc.doc_id, 'url': e1.url, 'type': 'entity'})
                target_vertex = await self.get_or_create_vertex(e2.label, data={'url': e2.url, 'type': 'entity'})
                edge = await self.get_or_create_edge(source_vertex, target_vertex, edge_type=rel)
                yield Document(doc_id = doc.doc_id, metadata = { 'url': e1.url, 'name': e1.label })
                #yield Document(doc_id = e2.url, metadata = { 'url': e2.url, 'name': e2.label }) # We're only indexing what has a doc_id

            tokens = self.analyze(doc.text)

            for i in range(len(tokens)-1):
                # Load words, linking by sequential co-occurrence
                logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i+1]))
                source_vertex = await self.get_or_create_vertex(tokens[i], data={'type': 'term'})
                target_vertex = await self.get_or_create_vertex(tokens[i+1], data={'type': 'term'})
                edge = await self.get_or_create_edge(source_vertex, target_vertex, data={'doc_id': doc.doc_id})

            doc_entity_labels = set([])
            for e1, _, e2 in doc.triples:
                doc_entity_labels.add(e1.label.lower())
                doc_entity_labels.add(e2.label.lower())

            # Order does not matter / a second loop over unique tokens and entities should help
            for token in set(tokens):
                # Load word synonyms, linking to original term

                #syns = set([ss.name().split('.')[0].replace('_', ' ') for ss in wn.synsets(token)])
                #syns = syns.difference(token)

                #for syn in syns:
                    #logger.debug("%s -[synonym]-> %s" % (token, syn))
                    #syn_vertex = await self.get_or_create_vertex(syn, data={'type': 'term'})
                    #edge = await self.get_or_create_edge(source_vertex, syn_vertex, edge_type='synonym')

                # Load word-entity occurrence

                for entity_label in doc_entity_labels:
                    if re.search(r'\b%s\b' % re.escape(token), entity_label):
                        logger.debug("%s -[contained_in]-> %s" % (token, entity_label))
                        entity_vertex = await self.get_or_create_vertex(entity_label, data={'type': 'entity'})
                        edge = await self.get_or_create_edge(source_vertex, entity_vertex, edge_type='contained_in')

            #yield doc

        await self.cluster.close()

    async def search(self, query, offset, limit):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

        graph = self.index_path if self.index_path else 'graph'

        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % graph)
            + load_gremlin_script('graph_of_entity_query'), {
                'queryTokens': query_tokens,
                'offset': offset,
                'limit': limit
            })
        results = await result_set.one()
        await self.cluster.close()

        return results
