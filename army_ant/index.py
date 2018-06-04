#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import configparser
import itertools
import json
import logging
import os
import re
import signal
from enum import Enum

import jpype
import psycopg2
from aiogremlin import Cluster
from aiohttp.client_exceptions import ClientConnectorError
from jpype import *

from army_ant.exception import ArmyAntException
from army_ant.reader import Document, Entity
from army_ant.util.text import analyze
from army_ant.util import load_gremlin_script, load_sql_script

logger = logging.getLogger(__name__)


class Index(object):
    PRELOADED = {}

    @staticmethod
    def __preloaded_key__(index_location, index_type):
        return '%s::%s' % (index_location, index_type)

    @staticmethod
    def factory(reader, index_location, index_type, loop):
        if index_type == 'gow':
            return GraphOfWord(reader, index_location, loop)
        elif index_type == 'goe':
            return GraphOfEntity(reader, index_location, loop)
        elif index_type == 'gow_batch':
            return GraphOfWordBatch(reader, index_location, loop)
        elif index_type == 'goe_batch':
            return GraphOfEntityBatch(reader, index_location, loop)
        elif index_type == 'gow_csv':
            return GraphOfWordCSV(reader, index_location, loop)
        elif index_type == 'goe_csv':
            return GraphOfEntityCSV(reader, index_location, loop)
        elif index_type.startswith('hgoe'):
            index_features = index_type.split(':')[1:]
            return HypergraphOfEntity(reader, index_location, index_features, loop)
        elif index_type == 'lucene':
            return LuceneEngine(reader, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    def open(index_location, index_type, loop):
        key = Index.__preloaded_key__(index_location, index_type)
        if key in Index.PRELOADED:
            return Index.PRELOADED[key]

        if index_type == 'gow':
            return GraphOfWord(None, index_location, loop)
        elif index_type == 'goe':
            return GraphOfEntity(None, index_location, loop)
        elif index_type == 'gow_batch':
            return GraphOfWordBatch(None, index_location, loop)
        elif index_type == 'goe_batch':
            return GraphOfEntityBatch(None, index_location, loop)
        elif index_type == 'gow_csv':
            return GraphOfWordCSV(None, index_location, loop)
        elif index_type == 'goe_csv':
            return GraphOfEntityCSV(None, index_location, loop)
        elif index_type == 'gremlin':
            return GremlinServerIndex(None, index_location, loop)
        elif index_type.startswith('hgoe'):
            index_features = index_type.split(':')[1:]
            return HypergraphOfEntity(None, index_location, index_features, loop)
        elif index_type == 'lucene':
            return LuceneEngine(None, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    async def preload(index_location, index_type, loop):
        index = Index.open(index_location, index_type, loop)
        await index.load()
        key = Index.__preloaded_key__(index_location, index_type)
        Index.PRELOADED[key] = index

    @staticmethod
    async def no_store(index):
        async for _ in index: pass

    def __init__(self, reader, index_location, loop):
        self.reader = reader
        self.index_location = index_location
        self.loop = loop

    @staticmethod
    def analyze(text):
        return analyze(text)

    async def load(self):
        pass

    async def index(self, features_location=None):
        """Indexes the documents and yields documents to store in the database."""
        raise ArmyAntException("Index not implemented for %s" % self.__class__.__name__)

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None):
        raise ArmyAntException("Search not implemented for %s" % self.__class__.__name__)

    async def inspect(self, feature, workdir='.'):
        raise ArmyAntException("Inspect not implemented for %s" % self.__class__.__name__)


class Result(object):
    def __init__(self, score, id, name, type=None, components=None):
        self.id = id
        self.name = name
        self.type = type
        self.score = score
        self.components = components

    def set_component(self, key, value):
        if self.components is None:
            self.components = []
        self.components[key] = value

    def unset_component(self, key):
        del self.components[key]
        if len(self.components) == 0:
            self.components = None

    def __getitem__(self, key):
        if key == 'id':
            return self.id
        elif key == 'name':
            return self.name
        elif key == 'type':
            return self.type
        elif key == 'score':
            return self.score
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return (key == 'id' and self.id or
                key == 'name' and self.name or
                key == 'type' and self.type or
                key == 'score' and self.score)

    def __repr__(self):
        return """{ "score": %f, "id": %s, "name": %s, "type": %s, "has_components": %s }""" % (
            self.score, self.id, self.name, self.type, ("true" if self.components else "false"))


class ResultSet(object):
    def __init__(self, results, num_docs, trace=None, trace_ascii=None):
        self.results = results
        self.num_docs = num_docs
        self.trace = trace
        self.trace_ascii = trace_ascii

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        self.iter = iter(self.results)
        return self.iter

    def __next__(self):
        return next(self.iter)

    # For compatibility with external implementations depending on dictionaries
    def __getitem__(self, key):
        if key == 'results':
            return self.results
        elif key == 'numDocs':
            return self.num_docs
        elif key == 'trace':
            return self.trace
        elif key == 'traceASCII':
            return self.trace_ascii
        else:
            raise KeyError

    def __contains__(self, key):
        return (key == 'results' and self.results or
                key == 'numDocs' and self.num_docs or
                key == 'trace' and self.trace or
                key == 'traceASCII' and self.trace_ascii)

    def __repr__(self):
        return "[ %s ]" % ', '.join([str(result) for result in self.results])


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


class GremlinServerIndex(ServiceIndex):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.graph = self.index_path if self.index_path else 'graph'

    async def get_or_create_vertex(self, vertex_name, data=None):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('get_or_create_vertex'),
            {'vertexName': vertex_name, 'data': data})
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def get_or_create_edge(self, source_vertex, target_vertex, edge_type='before', data=None):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('get_or_create_edge'), {
                'sourceID': source_vertex.id,
                'targetID': target_vertex.id,
                'edgeType': edge_type,
                'data': data
            })
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def to_edge_list(self, use_names=False):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('convert_to_edge_list'), {
                'useNames': use_names
            })
        async for edge in result_set:
            yield edge


class GraphOfWord(GremlinServerIndex):
    def __init__(self, reader, index_location, loop, window_size=3):
        super().__init__(reader, index_location, loop)
        self.window_size = window_size

    async def index(self, features_location=None):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            tokens = GraphOfWord.analyze(doc.text)

            for i in range(len(tokens) - self.window_size):
                for j in range(1, self.window_size + 1):
                    logger.debug("%s -> %s" % (tokens[i], tokens[i + j]))
                    source_vertex = await self.get_or_create_vertex(tokens[i])
                    target_vertex = await self.get_or_create_vertex(tokens[i + j])
                    await self.get_or_create_edge(
                        source_vertex, target_vertex, data={'doc_id': doc.doc_id})

            yield doc

        await self.cluster.close()

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None):
        try:
            self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        except ClientConnectorError as e:
            raise ArmyAntException("Could not connect to Gremlin Server on %s:%s" % (self.index_host, self.index_port))

        self.client = await self.cluster.connect()

        query_tokens = GraphOfWord.analyze(query)

        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('graph_of_word_query'), {
                'queryTokens': query_tokens,
                'offset': offset,
                'limit': limit
            })
        results = await result_set.one()
        await self.cluster.close()

        return results


class GraphOfEntity(GremlinServerIndex):
    async def index(self, features_location=None):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            # Load entities and relations (knowledge base)
            for (e1, rel, e2) in doc.triples:
                logger.debug("%s -[%s]-> %s" % (e1.label, rel, e2.label))
                source_vertex = await self.get_or_create_vertex(e1.label, data={'doc_id': doc.doc_id, 'url': e1.url,
                                                                                'type': 'entity'})
                target_vertex = await self.get_or_create_vertex(e2.label, data={'url': e2.url, 'type': 'entity'})
                edge = await self.get_or_create_edge(source_vertex, target_vertex, edge_type=rel)
                yield Document(doc_id=doc.doc_id, metadata={'url': e1.url, 'name': e1.label})
                # yield Document(doc_id = e2.url, metadata = { 'url': e2.url, 'name': e2.label }) # We're only
                # indexing what has a doc_id

            tokens = GraphOfEntity.analyze(doc.text)

            for i in range(len(tokens) - 1):
                # Load words, linking by sequential co-occurrence
                logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i + 1]))
                source_vertex = await self.get_or_create_vertex(tokens[i], data={'type': 'term'})
                target_vertex = await self.get_or_create_vertex(tokens[i + 1], data={'type': 'term'})
                await self.get_or_create_edge(source_vertex, target_vertex, data={'doc_id': doc.doc_id})

            doc_entity_labels = set([])
            for e1, _, e2 in doc.triples:
                doc_entity_labels.add(e1.label.lower())
                doc_entity_labels.add(e2.label.lower())

            # Order does not matter / a second loop over unique tokens and entities should help
            for token in set(tokens):
                # Load word synonyms, linking to original term

                # syns = set([ss.name().split('.')[0].replace('_', ' ') for ss in wn.synsets(token)])
                # syns = syns.difference(token)

                # for syn in syns:
                # logger.debug("%s -[synonym]-> %s" % (token, syn))
                # syn_vertex = await self.get_or_create_vertex(syn, data={'type': 'term'})
                # edge = await self.get_or_create_edge(source_vertex, syn_vertex, edge_type='synonym')

                # Load word-entity occurrence

                source_vertex = await self.get_or_create_vertex(token, data={'type': 'term'})

                for entity_label in doc_entity_labels:
                    if re.search(r'\b%s\b' % re.escape(token), entity_label):
                        logger.debug("%s -[contained_in]-> %s" % (token, entity_label))
                        entity_vertex = await self.get_or_create_vertex(entity_label, data={'type': 'entity'})
                        await self.get_or_create_edge(source_vertex, entity_vertex, edge_type='contained_in')

                        # yield doc

        await self.cluster.close()

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None):
        try:
            self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        except ClientConnectorError as e:
            raise ArmyAntException("Could not connect to Gremlin Server on %s:%s" % (self.index_host, self.index_port))

        self.client = await self.cluster.connect()

        query_tokens = GraphOfEntity.analyze(query)

        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('graph_of_entity_query'), {
                'queryTokens': query_tokens,
                'offset': offset,
                'limit': limit
            })
        results = await result_set.one()
        await self.cluster.close()

        return results


# Used for composition within *Batch graphs
class PostgreSQLGraph(object):
    def create_postgres_schema(self, conn):
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS nodes")
        c.execute("DROP TABLE IF EXISTS edges")
        c.execute("CREATE TABLE nodes (node_id BIGINT, label TEXT, attributes JSONB)")
        c.execute(
            "CREATE TABLE edges (edge_id BIGINT, label TEXT, attributes JSONB, source_node_id BIGINT, target_node_id BIGINT)")
        conn.commit()

    def create_vertex_postgres(self, conn, vertex_id, label, attributes):
        c = conn.cursor()
        properties = {}
        for k, v in attributes.items():
            properties[k] = [{'id': self.next_property_id, 'value': v}]
            self.next_property_id += 1
        c.execute("INSERT INTO nodes VALUES (%s, %s, %s)", (vertex_id, label, json.dumps(properties)))

    def create_edge_postgres(self, conn, edge_id, label, source_vertex_id, target_vertex_id, attributes={}):
        c = conn.cursor()
        c.execute("INSERT INTO edges VALUES (%s, %s, %s, %s, %s)",
                  (edge_id, label, json.dumps(attributes), source_vertex_id, target_vertex_id))

    def update_vertex_attribute(self, conn, vertex_id, attr_name, attr_value):
        c = conn.cursor()
        c.execute(
            "UPDATE nodes SET attributes = jsonb_set(attributes, '{%s}', '[{\"id\": %s, \"value\": \"%s\"}]', true) WHERE node_id = %%s" % (
                attr_name, self.next_property_id, attr_value), (vertex_id,))
        self.next_property_id += 1

    def load_to_postgres(self, conn, doc):
        raise ArmyAntException("Load function not implemented for %s" % self.__class__.__name__)

    def postgres_to_graphson(self, conn, filename):
        logger.info("Converting PostgreSQL nodes and edges into the GraphSON format")

        with open(filename, 'w') as f:
            c = conn.cursor()
            c.execute(load_sql_script('to_graphson'))

            for row in c:
                node = {'id': row[0], 'label': row[1]}
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

    async def index(self, features_location=None, pgonly=False):
        self.next_vertex_id = 1
        self.next_edge_id = 1
        self.next_property_id = 1
        self.vertex_cache = {}

        conn = psycopg2.connect("dbname='army_ant' user='army_ant' host='localhost'")
        self.create_postgres_schema(conn)

        for doc in self.reader:
            logger.info("Building vertex and edge records for %s" % doc.doc_id)
            logger.debug(doc.text)
            for index_doc in self.load_to_postgres(conn, doc):
                yield index_doc

        conn.commit()

        if not pgonly: self.postgres_to_graphson(conn, '/tmp/graph.json')

        conn.close()

        if not pgonly: await self.load_to_gremlin_server('/tmp/graph.json')
        # yield None


class GraphOfWordBatch(PostgreSQLGraph, GraphOfWord):
    def get_or_create_term_vertex(self, conn, token):
        if token in self.vertex_cache:
            vertex_id = self.vertex_cache[token]
        else:
            vertex_id = self.next_vertex_id
            self.vertex_cache[token] = vertex_id
            self.next_vertex_id += 1
            self.create_vertex_postgres(conn, vertex_id, 'term', {'name': token})

        return vertex_id

    def load_to_postgres(self, conn, doc):
        tokens = GraphOfWordBatch.analyze(doc.text)

        for i in range(len(tokens) - self.window_size):
            for j in range(1, self.window_size + 1):
                source_vertex_id = self.get_or_create_term_vertex(conn, tokens[i])
                target_vertex_id = self.get_or_create_term_vertex(conn, tokens[i + j])

                logger.debug("%s (%d) -> %s (%s)" % (tokens[i], source_vertex_id, tokens[i + j], target_vertex_id))
                self.create_edge_postgres(conn, self.next_edge_id, 'in_window_of', source_vertex_id, target_vertex_id,
                                          {'doc_id': doc.doc_id})
                self.next_edge_id += 1

        conn.commit()

        yield doc


class GraphOfEntityBatch(PostgreSQLGraph, GraphOfEntity):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.vertices_with_doc_id = set([])

    def get_or_create_entity_vertex(self, conn, entity, doc_id=None):
        cache_key = 'entity::%s' % entity.label

        if cache_key in self.vertex_cache:
            vertex_id = self.vertex_cache[cache_key]
            if doc_id and not vertex_id in self.vertices_with_doc_id:
                self.update_vertex_attribute(conn, vertex_id, 'doc_id', doc_id)
                self.vertices_with_doc_id.add(vertex_id)
        else:
            vertex_id = self.next_vertex_id
            self.vertex_cache[cache_key] = vertex_id
            self.next_vertex_id += 1

            data = {'type': 'entity', 'name': entity.label}

            if entity.url:
                data['url'] = entity.url

            if doc_id:
                data['doc_id'] = doc_id
                self.vertices_with_doc_id.add(vertex_id)

            self.create_vertex_postgres(conn, vertex_id, 'entity', data)

        return vertex_id

    def get_or_create_term_vertex(self, conn, term):
        cache_key = 'term::%s' % term

        if cache_key in self.vertex_cache:
            vertex_id = self.vertex_cache[cache_key]
        else:
            vertex_id = self.next_vertex_id
            self.vertex_cache[cache_key] = vertex_id
            self.next_vertex_id += 1
            self.create_vertex_postgres(conn, vertex_id, 'term', {'type': 'term', 'name': term})

        return vertex_id

    def load_to_postgres(self, conn, doc):
        # Load entities and relations (knowledge base)
        for (e1, _, e2) in doc.triples:
            logger.debug("%s -[related_to]-> %s" % (e1.label, e2.label))
            source_vertex_id = self.get_or_create_entity_vertex(conn, e1, doc_id=doc.doc_id)
            target_vertex_id = self.get_or_create_entity_vertex(conn, e2)
            self.create_edge_postgres(conn, self.next_edge_id, 'related_to', source_vertex_id, target_vertex_id)
            self.next_edge_id += 1
            metadata = {'name': e1.label}
            if e1.url: metadata['url'] = e1.url
            # yield Document(doc_id = doc.doc_id, metadata = metadata) # We're only indexing what has a doc_id / XXX
            # this was wrong, because entities never have a doc_id, unless they come from a doc, so just return doc,
            # right?

        tokens = GraphOfEntityBatch.analyze(doc.text)

        for i in range(len(tokens) - 1):
            # Load words, linking by sequential co-occurrence
            logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i + 1]))
            source_vertex_id = self.get_or_create_term_vertex(conn, tokens[i])
            target_vertex_id = self.get_or_create_term_vertex(conn, tokens[i + 1])
            self.create_edge_postgres(conn, self.next_edge_id, 'before', source_vertex_id, target_vertex_id,
                                      {'doc_id': doc.doc_id})
            self.next_edge_id += 1

        doc_entity_labels = set([])
        for e1, _, e2 in doc.triples:
            doc_entity_labels.add(e1.label.lower())
            doc_entity_labels.add(e2.label.lower())

        # Order does not matter / a second loop over unique tokens and entities should help
        for token in set(tokens):
            # Load word-entity occurrence
            source_vertex_id = self.get_or_create_term_vertex(conn, token)
            for entity_label in doc_entity_labels:
                if re.search(r'\b%s\b' % re.escape(token), entity_label):
                    logger.debug("%s -[contained_in]-> %s" % (token, entity_label))
                    entity_vertex_id = self.get_or_create_entity_vertex(conn, Entity(entity_label))
                    self.create_edge_postgres(conn, self.next_edge_id, 'contained_in', source_vertex_id,
                                              entity_vertex_id)

        conn.commit()

        yield doc


class GraphOfWordCSV(GraphOfWordBatch):
    async def index(self, features_location=None, pgonly=True):
        if os.path.exists(self.index_location):
            raise ArmyAntException("%s already exists" % self.index_location)

        os.mkdir(self.index_location)

        async for item in super().index(pgonly=pgonly):
            yield item

        conn = psycopg2.connect("dbname='army_ant' user='army_ant' host='localhost'")
        c = conn.cursor()

        logging.info("Creating term nodes CSV file")
        with open(os.path.join(self.index_location, 'term-nodes.csv'), 'w') as f:
            c.copy_expert("""
            COPY (SELECT node_id AS "node_id:ID", attributes->'name'->0->>'value' AS name, label AS ":LABEL" FROM nodes)
            TO STDOUT WITH CSV HEADER
            """, f)

        logging.info("Creating in_window_of edges CSV file")
        with open(os.path.join(self.index_location, 'in_window_of-edges.csv'), 'w') as f:
            c.copy_expert("""
            COPY (SELECT source_node_id AS ":START_ID", attributes->>'doc_id' AS doc_id, target_node_id AS ":END_ID", label AS ":TYPE" FROM edges)
            TO STDOUT WITH CSV HEADER
            """, f)


class GraphOfEntityCSV(GraphOfEntityBatch):
    async def index(self, features_location=None, pgonly=True):
        if os.path.exists(self.index_location):
            raise ArmyAntException("%s already exists" % self.index_location)

        os.mkdir(self.index_location)

        async for item in super().index(pgonly=pgonly):
            yield item

        conn = psycopg2.connect("dbname='army_ant' user='army_ant' host='localhost'")
        c = conn.cursor()

        logging.info("Creating term nodes CSV file")
        with open(os.path.join(self.index_location, 'term-nodes.csv'), 'w') as f:
            c.copy_expert("""
            COPY (
                SELECT
                    node_id AS "node_id:ID",
                    attributes->'name'->0->>'value' AS name,
                    attributes->'type'->0->>'value' AS type,
                    label AS ":LABEL"
                FROM nodes
                WHERE label = 'term'
            )
            TO STDOUT WITH CSV HEADER
            """, f)

        logging.info("Creating entity nodes CSV file")
        with open(os.path.join(self.index_location, 'entity-nodes.csv'), 'w') as f:
            c.copy_expert("""
            COPY (
                SELECT
                    node_id AS "node_id:ID",
                    regexp_replace(attributes->'name'->0->>'value', E'[\\n\\r]', ' ', 'g') AS name,
                    attributes->'type'->0->>'value' AS type,
                    attributes->'doc_id'->0->>'value' AS doc_id,
                    label AS ":LABEL"
                FROM nodes
                WHERE label = 'entity'
            )
            TO STDOUT WITH CSV HEADER
            """, f)

        logging.info("Creating before edges CSV file")
        with open(os.path.join(self.index_location, 'before-edges.csv'), 'w') as f:
            c.copy_expert("""
            COPY (
                SELECT
                    source_node_id AS ":START_ID",
                    attributes->>'doc_id' AS doc_id,
                    target_node_id AS ":END_ID",
                    label AS ":TYPE"
                FROM edges
                WHERE label = 'before'
            )
            TO STDOUT WITH CSV HEADER
            """, f)

        logging.info("Creating related_to edges CSV file")
        with open(os.path.join(self.index_location, 'related_to-edges.csv'), 'w') as f:
            c.copy_expert("""
            COPY (
                SELECT
                    source_node_id AS ":START_ID",
                    target_node_id AS ":END_ID",
                    label AS ":TYPE"
                FROM edges
                WHERE label = 'related_to'
            )
            TO STDOUT WITH CSV HEADER
            """, f)

        logging.info("Creating contained_in edges CSV file")
        with open(os.path.join(self.index_location, 'contained_in-edges.csv'), 'w') as f:
            c.copy_expert("""
            COPY (
                SELECT
                    source_node_id AS ":START_ID",
                    target_node_id AS ":END_ID",
                    label AS ":TYPE"
                FROM edges
                WHERE label = 'contained_in'
            )
            TO STDOUT WITH CSV HEADER
            """, f)


def handler(signum, frame): raise KeyboardInterrupt


class JavaIndex(Index):
    BLOCK_SIZE = 5000
    VERSION = '0.4-SNAPSHOT'
    CLASSPATH = 'external/java-impl/target/java-impl-%s-jar-with-dependencies.jar' % VERSION
    INSTANCES = {}

    config = configparser.ConfigParser()
    config.read('server.cfg')
    MEMORY_MB = int(config['DEFAULT'].get('jvm_memory', '5120'))

    if not isJVMStarted():
        startJVM(
            jpype.getDefaultJVMPath(),
            '-Djava.class.path=%s' % CLASSPATH,
            '-Xms%dm' % MEMORY_MB,
            '-Xmx%dm' % MEMORY_MB)

    signal.signal(signal.SIGINT, handler)

    armyant = JPackage('armyant')
    JDocument = armyant.structures.Document
    JTriple = armyant.structures.Triple
    JTripleInstance = JClass("armyant.structures.Triple$Instance")


class HypergraphOfEntity(JavaIndex):
    class Feature(Enum):
        syns = 'SYNONYMS'
        context = 'CONTEXT'
        weight = 'WEIGHT'
        prune = 'PRUNE'

    class Task(Enum):
        document_retrieval = 'DOCUMENT_RETRIEVAL'
        entity_retrieval = 'ENTITY_RETRIEVAL'
        term_retrieval = 'TERM_RETRIEVAL'

    class RankingFunction(Enum):
        entity_weight = 'ENTITY_WEIGHT'
        jaccard = 'JACCARD_SCORE'
        random_walk = 'RANDOM_WALK_SCORE'
        biased_random_walk = 'BIASED_RANDOM_WALK_SCORE'

    JHypergraphOfEntityInMemory = JavaIndex.armyant.hgoe.HypergraphOfEntity
    JFeature = JClass("armyant.hgoe.HypergraphOfEntity$Feature")
    JRankingFunction = JClass("armyant.hgoe.HypergraphOfEntity$RankingFunction")
    JTask = JClass("armyant.hgoe.HypergraphOfEntity$Task")

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.index_features = [HypergraphOfEntity.Feature[index_feature] for index_feature in index_features]

    async def load(self):
        if self.index_location in JavaIndex.INSTANCES:
            logger.warning("%s is already loaded, skipping" % self.index_location)
            return
        features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                    self.index_features]
        JavaIndex.INSTANCES[self.index_location] = HypergraphOfEntity.JHypergraphOfEntityInMemory(
            self.index_location, java.util.Arrays.asList(features))

    async def index(self, features_location=None):
        try:
            index_features_str = ':'.join([index_feature.value for index_feature in self.index_features])
            features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                        self.index_features]

            if HypergraphOfEntity.Feature.context in self.index_features:
                if features_location is None:
                    raise ArmyAntException("Must provide a features_location pointing to a directory")
                if not 'word2vec_simnet.graphml.gz' in os.listdir(features_location):
                    raise ArmyAntException("Must provide a 'word2vec_simnet.graphml.gz' file within features directory")

            hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                self.index_location, java.util.Arrays.asList(features), features_location, True)

            corpus = []
            for doc in self.reader:
                logger.debug("Preloading document %s (%d triples)" % (doc.doc_id, len(doc.triples)))

                triples = []

                for s, p, o in doc.triples:
                    try:
                        triples.append(HypergraphOfEntity.JTriple(
                            HypergraphOfEntity.JTripleInstance(s.uri, s.label),
                            HypergraphOfEntity.JTripleInstance(p.uri, p.label),
                            HypergraphOfEntity.JTripleInstance(o.uri, p.label)))
                    except:
                        logger.warning("Triple (%s, %s, %s) skipped" % (s, p, o))

                jDoc = HypergraphOfEntity.JDocument(
                    JString(doc.doc_id), doc.title, JString(doc.text), java.util.Arrays.asList(triples))
                corpus.append(jDoc)

                if len(corpus) % (HypergraphOfEntity.BLOCK_SIZE // 10) == 0:
                    logger.info("%d documents preloaded" % len(corpus))

                if len(corpus) >= HypergraphOfEntity.BLOCK_SIZE:
                    logger.info("Indexing batch of %d documents using %s" % (len(corpus), index_features_str))
                    hgoe.indexCorpus(java.util.Arrays.asList(corpus))
                    corpus = []

                yield Document(
                    doc_id=doc.doc_id,
                    metadata={
                        'url': doc.metadata.get('url'),
                        'name': doc.metadata.get('name')
                    })

            if len(corpus) > 0:
                logger.info("Indexing batch of %d documents using %s" % (len(corpus), index_features_str))
                hgoe.indexCorpus(java.util.Arrays.asList(corpus))

            hgoe.postProcessing()

            hgoe.save()
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())
        finally:
            shutdownJVM()

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None):
        if ranking_function:
            try:
                ranking_function = HypergraphOfEntity.RankingFunction[ranking_function]
            except (JavaException, KeyError) as e:
                logger.error("Could not use '%s' as the ranking function" % ranking_function)
                ranking_function = HypergraphOfEntity.RankingFunction['random_walk']
        else:
            ranking_function = HypergraphOfEntity.RankingFunction['random_walk']

        if task:
            try:
                task = HypergraphOfEntity.Task[task]
            except (JavaException, KeyError) as e:
                logger.error("Could not use '%s' as the ranking function" % ranking_function)
                task = HypergraphOfEntity.Task['document_retrieval']
        else:
            task = HypergraphOfEntity.Task['document_retrieval']

        logger.info("Using '%s' as ranking function" % ranking_function.value)
        ranking_function = HypergraphOfEntity.JRankingFunction.valueOf(ranking_function.value)

        j_ranking_params = jpype.java.util.HashMap()
        if ranking_params:
            logger.info("Using ranking parameters %s" % ranking_params)
            for k, v in ranking_params.items():
                j_ranking_params.put(k, v)
        ranking_params = j_ranking_params

        results = []
        num_docs = 0
        trace = None
        try:
            if self.index_location in HypergraphOfEntity.INSTANCES:
                hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            else:
                features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                            self.index_features]
                hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                    self.index_location, java.util.Arrays.asList(features))
                HypergraphOfEntity.INSTANCES[self.index_location] = hgoe

            task = HypergraphOfEntity.JTask.valueOf(task.value)
            results = hgoe.search(query, offset, limit, task, ranking_function, ranking_params)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in itertools.islice(results, offset, offset + limit)]
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())

    async def inspect(self, feature, workdir):
        try:
            if self.index_location in HypergraphOfEntity.INSTANCES:
                hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            else:
                features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                            self.index_features]
                hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                    self.index_location, java.util.Arrays.asList(features))
                HypergraphOfEntity.INSTANCES[self.index_location] = hgoe

            hgoe.inspect(feature, workdir)
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())


class LuceneEngine(JavaIndex):
    class RankingFunction(Enum):
        tf_idf = 'TF_IDF'
        bm25 = 'BM25'
        dfr = 'DFR'

    JLuceneEngine = JavaIndex.armyant.lucene.LuceneEngine
    JRankingFunction = JClass("armyant.lucene.LuceneEngine$RankingFunction")

    async def index(self, features_location=None):
        try:
            lucene = LuceneEngine.JLuceneEngine(self.index_location)
            lucene.open()

            corpus = []
            for doc in self.reader:
                logger.debug("Preloading document %s (%d triples)" % (doc.doc_id, len(doc.triples)))
                triples = list(map(lambda t: LuceneEngine.JTriple(
                    HypergraphOfEntity.JTripleInstance(t[0].uri, t[0].label),
                    HypergraphOfEntity.JTripleInstance(t[1].uri, t[1].label),
                    HypergraphOfEntity.JTripleInstance(t[2].uri, t[2].label)), doc.triples))
                jDoc = LuceneEngine.JDocument(
                    JString(doc.doc_id), doc.title, JString(doc.text), java.util.Arrays.asList(triples))
                corpus.append(jDoc)
                if len(corpus) % (LuceneEngine.BLOCK_SIZE // 10) == 0:
                    logger.info("%d documents preloaded" % len(corpus))

                if len(corpus) >= LuceneEngine.BLOCK_SIZE:
                    logger.info("Indexing batch of %d documents" % len(corpus))
                    lucene.indexCorpus(java.util.Arrays.asList(corpus))
                    corpus = []

                yield Document(
                    doc_id=doc.doc_id,
                    metadata={
                        'url': doc.metadata.get('url'),
                        'name': doc.metadata.get('name')
                    })

            if len(corpus) > 0:
                logger.info("Indexing batch of %d documents" % len(corpus))
                lucene.indexCorpus(java.util.Arrays.asList(corpus))

            lucene.close()
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())
        finally:
            shutdownJVM()

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None):
        if ranking_function:
            try:
                ranking_function = LuceneEngine.RankingFunction[ranking_function]
            except (JavaException, KeyError) as e:
                logger.error("Could not use '%s' as the ranking function" % ranking_function)
                ranking_function = LuceneEngine.RankingFunction['tf_idf']
        else:
            ranking_function = LuceneEngine.RankingFunction['tf_idf']

        logger.info("Using '%s' as ranking function" % ranking_function.value)
        ranking_function = LuceneEngine.JRankingFunction.valueOf(ranking_function.value)

        j_ranking_params = jpype.java.util.HashMap()
        if ranking_params:
            logger.info("Using ranking parameters %s" % ranking_params)
            for k, v in ranking_params.items():
                j_ranking_params.put(k, v)
        ranking_params = j_ranking_params

        results = []
        num_docs = 0
        trace = None
        try:
            if self.index_location in LuceneEngine.INSTANCES:
                lucene = LuceneEngine.INSTANCES[self.index_location]
            else:
                lucene = LuceneEngine.JLuceneEngine(self.index_location)
                LuceneEngine.INSTANCES[self.index_location] = lucene

            results = lucene.search(query, offset, limit, ranking_function, ranking_params)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in itertools.islice(results, offset, offset + limit)]
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())
