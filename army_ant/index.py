#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import logging, string, asyncio, pymongo, re, json, psycopg2, os, jpype, itertools, json
from enum import Enum
from jpype import *
from aiogremlin import Cluster
from aiogremlin.gremlin_python.structure.graph import Vertex
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from nltk import word_tokenize
from nltk.corpus import stopwords, wordnet as wn
from army_ant.reader import Document, Entity
from army_ant.text import analyze
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.exception import ArmyAntException

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
        elif index_type == 'hgoe':
            return HypergraphOfEntity(reader, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    def open(index_location, index_type, loop):
        key = Index.__preloaded_key__(index_location, index_type)
        if key in Index.PRELOADED: return Index.PRELOADED[key]

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
        elif index_type == 'hgoe':
            return HypergraphOfEntity(None, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    async def preload(index_location, index_type, loop):
        index = Index.open(index_location, index_type, loop)
        await index.load()
        key = Index.__preloaded_key__(index_location, index_type)
        Index.PRELOADED[key] = index

    def __init__(self, reader, index_location, loop):
        self.reader = reader
        self.index_location = index_location
        self.loop = loop

    def analyze(self, text):
        return analyze(text)

    """Indexes the documents and yields documents to store in the database."""
    async def index(self):
        raise ArmyAntException("Index not implemented for %s" % self.__class__.__name__)

    async def search(self, query, offset, limit, ranking_function=None):
        raise ArmyAntException("Search not implemented for %s" % self.__class__.__name__)

    async def load(self):
        raise ArmyAntException("Load not implemented for %s" % self.__class__.__name__)

class Result(object):
    def __init__(self, doc_id, score, components=None):
        self.doc_id = doc_id
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
        if key == 'docID':
            return self.doc_id
        elif key == 'score':
            return self.score
        else:
            raise KeyError

    def __contains__(self, key):
        return (key == 'docID' and self.doc_id or
                key == 'score' and self.score)

    def __repr__(self):
        return """{ "docID": %s, "score": %f, "has_components": %s }""" % (
            self.doc_id, self.score, ("true" if self.components else "false"))

class ResultSet(object):
    def __init__(self, results, num_docs, trace=None, trace_ascii=None):
        self.results = results
        self.num_docs = num_docs
        self.trace = trace
        self.trace_ascii = trace_ascii

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
        return results[0] if len (results) > 0 else None

    async def to_edge_list(use_names=False):
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

    async def search(self, query, offset, limit, ranking_function=None):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

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

                source_vertex = await self.get_or_create_vertex(token, data={'type': 'term'})

                for entity_label in doc_entity_labels:
                    if re.search(r'\b%s\b' % re.escape(token), entity_label):
                        logger.debug("%s -[contained_in]-> %s" % (token, entity_label))
                        entity_vertex = await self.get_or_create_vertex(entity_label, data={'type': 'entity'})
                        edge = await self.get_or_create_edge(source_vertex, entity_vertex, edge_type='contained_in')

            #yield doc

        await self.cluster.close()

    async def search(self, query, offset, limit, ranking_function=None):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        query_tokens = self.analyze(query)

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
        c.execute("CREATE TABLE edges (edge_id BIGINT, label TEXT, attributes JSONB, source_node_id BIGINT, target_node_id BIGINT)")
        conn.commit()

    def create_vertex_postgres(self, conn, vertex_id, label, attributes):
        c = conn.cursor()
        properties = {}
        for k, v in attributes.items():
            properties[k] = [{ 'id': self.next_property_id, 'value': v }]
            self.next_property_id += 1
        c.execute("INSERT INTO nodes VALUES (%s, %s, %s)", (vertex_id, label, json.dumps(properties)))

    def create_edge_postgres(self, conn, edge_id, label, source_vertex_id, target_vertex_id, attributes={}):
        c = conn.cursor()
        c.execute("INSERT INTO edges VALUES (%s, %s, %s, %s, %s)", (edge_id, label, json.dumps(attributes), source_vertex_id, target_vertex_id))
    
    def update_vertex_attribute(self, conn, vertex_id, attr_name, attr_value):
        c = conn.cursor()
        c.execute(
            "UPDATE nodes SET attributes = jsonb_set(attributes, '{%s}', '[{\"id\": %s, \"value\": \"%s\"}]', true) WHERE node_id = %%s" % (
                attr_name, self.next_property_id, attr_value), (vertex_id, ))
        self.next_property_id += 1

    def load_to_postgres(self, conn, doc):
        raise ArmyAntException("Load function not implemented for %s" % self.__class__.__name__)

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

    async def index(self, pgonly=False):
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
        #yield None

class GraphOfWordBatch(PostgreSQLGraph,GraphOfWord):
    def get_or_create_term_vertex(self, conn, token):
        if token in self.vertex_cache:
            vertex_id = self.vertex_cache[token]
        else:
            vertex_id = self.next_vertex_id
            self.vertex_cache[token] = vertex_id
            self.next_vertex_id += 1
            self.create_vertex_postgres(conn, vertex_id, 'term', { 'name': token })

        return vertex_id

    def load_to_postgres(self, conn, doc):
        tokens = self.analyze(doc.text)

        for i in range(len(tokens)-self.window_size):
            for j in range(1, self.window_size + 1):
                source_vertex_id = self.get_or_create_term_vertex(conn, tokens[i])
                target_vertex_id = self.get_or_create_term_vertex(conn, tokens[i+j])

                logger.debug("%s (%d) -> %s (%s)" % (tokens[i], source_vertex_id, tokens[i+j], target_vertex_id))
                self.create_edge_postgres(conn, self.next_edge_id, 'in_window_of', source_vertex_id, target_vertex_id, { 'doc_id': doc.doc_id })
                self.next_edge_id += 1

        conn.commit()

        yield doc

class GraphOfEntityBatch(PostgreSQLGraph,GraphOfEntity):
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

            data = { 'type': 'entity', 'name': entity.label }

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
            self.create_vertex_postgres(conn, vertex_id, 'term', { 'type': 'term', 'name': term })

        return vertex_id

    def load_to_postgres(self, conn, doc):
        # Load entities and relations (knowledge base)
        for (e1, _, e2) in doc.triples:
            logger.debug("%s -[related_to]-> %s" % (e1.label, e2.label))
            source_vertex_id = self.get_or_create_entity_vertex(conn, e1, doc_id=doc.doc_id)
            target_vertex_id = self.get_or_create_entity_vertex(conn, e2)
            self.create_edge_postgres(conn, self.next_edge_id, 'related_to', source_vertex_id, target_vertex_id)
            self.next_edge_id += 1
            metadata = { 'name': e1.label }
            if e1.url: metadata['url'] = e1.url
            #yield Document(doc_id = doc.doc_id, metadata = metadata) # We're only indexing what has a doc_id / XXX this was wrong, because entities never have a doc_id, unless they come from a doc, so just return doc, right?

        tokens = self.analyze(doc.text)

        for i in range(len(tokens)-1):
            # Load words, linking by sequential co-occurrence
            logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i+1]))
            source_vertex_id = self.get_or_create_term_vertex(conn, tokens[i])
            target_vertex_id = self.get_or_create_term_vertex(conn, tokens[i+1])
            self.create_edge_postgres(conn, self.next_edge_id, 'before', source_vertex_id, target_vertex_id, {'doc_id': doc.doc_id})
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
                    self.create_edge_postgres(conn, self.next_edge_id, 'contained_in', source_vertex_id, entity_vertex_id)

        conn.commit()

        yield doc

class GraphOfWordCSV(GraphOfWordBatch):
    async def index(self):
        if os.path.exists(self.index_location):
            raise ArmyAntException("%s already exists" % self.index_location)

        os.mkdir(self.index_location)

        async for item in super().index(pgonly=True):
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
    async def index(self):
        if os.path.exists(self.index_location):
            raise ArmyAntException("%s already exists" % self.index_location)

        os.mkdir(self.index_location)

        async for item in super().index(pgonly=True):
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

class HypergraphOfEntity(Index):
    BLOCK_SIZE = 5000
    CLASSPATH = 'external/hypergraph-of-entity/target/hypergraph-of-entity-0.1-SNAPSHOT-jar-with-dependencies.jar'
    MEMORY_MB = 5120
    INSTANCES = {}

    class RankingFunction(Enum):
        entity_weight = 'ENTITY_WEIGHT'
        jaccard = 'JACCARD_SCORE'
        random_walk = 'RANDOM_WALK_SCORE'

    def init(self):
        if isJVMStarted(): return

        startJVM(
            jpype.getDefaultJVMPath(),
            '-Djava.class.path=%s' % HypergraphOfEntity.CLASSPATH,
            '-Xms%dm' % HypergraphOfEntity.MEMORY_MB,
            '-Xmx%dm' % HypergraphOfEntity.MEMORY_MB)

        package = JPackage('armyant.hgoe')
        HypergraphOfEntity.JHypergraphOfEntityInMemory = package.inmemory.HypergraphOfEntityInMemoryGrph
        HypergraphOfEntity.JDocument = package.structures.Document
        HypergraphOfEntity.JTriple = package.structures.Triple
        HypergraphOfEntity.JRankingFunction = JClass("armyant.hgoe.inmemory.HypergraphOfEntityInMemoryGrph$RankingFunction")

    async def load(self):
        self.init()
        if self.index_location in HypergraphOfEntity.INSTANCES:
            logger.warn("%s is already loaded, skipping" % self.index_location)
            return
        HypergraphOfEntity.INSTANCES[self.index_location] = HypergraphOfEntity.JHypergraphOfEntityInMemory(self.index_location)

    async def index(self):
        self.init()

        try:
            hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(self.index_location, True)
            
            corpus = []
            for doc in self.reader:
                logger.debug("Preloading document %s (%d triples)" % (doc.doc_id, len(doc.triples)))
                triples = list(map(lambda t: HypergraphOfEntity.JTriple(t[0].label, t[1], t[2].label), doc.triples))
                jDoc = HypergraphOfEntity.JDocument(
                    JString(doc.doc_id), JString(doc.entity), JString(doc.text), java.util.Arrays.asList(triples))
                corpus.append(jDoc)
                if len(corpus) % (HypergraphOfEntity.BLOCK_SIZE // 10) == 0:
                    logger.info("%d documents preloaded" % len(corpus))

                if len(corpus) >= HypergraphOfEntity.BLOCK_SIZE:
                    logger.info("Indexing batch of %d documents" % len(corpus))
                    hgoe.indexCorpus(java.util.Arrays.asList(corpus))
                    corpus = []

                yield Document(
                    doc_id = doc.doc_id,
                    metadata = {
                        'url': doc.metadata.get('url'),
                        'name': doc.metadata.get('name')
                    })

            if len(corpus) > 0:
                logger.info("Indexing batch of %d documents" % len(corpus))
                hgoe.indexCorpus(java.util.Arrays.asList(corpus))

            hgoe.postProcessing()

            hgoe.save()
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

    async def search(self, query, offset, limit, ranking_function=None):
        self.init()

        if ranking_function:
            ranking_function = HypergraphOfEntity.RankingFunction[ranking_function]
        else:
            ranking_function = HypergraphOfEntity.RankingFunction['random_walk']

        logger.info("Using '%s' as ranking function" % ranking_function.value)
        ranking_function = HypergraphOfEntity.JRankingFunction.valueOf(ranking_function.value)

        results = []
        num_docs = 0
        trace = None
        try:
            if self.index_location in HypergraphOfEntity.INSTANCES:
                hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            else:
                hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(self.index_location)
                HypergraphOfEntity.INSTANCES[self.index_location] = hgoe
            
            results = hgoe.search(query, ranking_function)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getDocID(), result.getScore())
                       for result in itertools.islice(results, offset, offset+limit)]
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())
