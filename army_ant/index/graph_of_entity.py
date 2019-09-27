#!/usr/bin/env python
#
# graph_of_entity.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging
import os
import re

import psycopg2
from aiogremlin import Cluster
from aiohttp.client_exceptions import ClientConnectorError

from army_ant.exception import ArmyAntException
from army_ant.index import GremlinServerIndex, PostgreSQLGraph
from army_ant.reader import Document, Entity
from army_ant.util import load_gremlin_script

logger = logging.getLogger(__name__)


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
                await self.get_or_create_edge(source_vertex, target_vertex, edge_type=rel)
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

    async def search(self, query, offset, limit, query_type=None, task=None,
                     base_index_location=None, base_index_type=None,
                     ranking_function=None, ranking_params=None, debug=False):
        try:
            self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        except ClientConnectorError:
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


class GraphOfEntityBatch(PostgreSQLGraph, GraphOfEntity):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.vertices_with_doc_id = set([])

    def get_or_create_entity_vertex(self, conn, entity, doc_id=None):
        cache_key = 'entity::%s' % entity.label

        if cache_key in self.vertex_cache:
            vertex_id = self.vertex_cache[cache_key]
            if doc_id and vertex_id not in self.vertices_with_doc_id:
                self.update_vertex_attribute(conn, vertex_id, 'doc_id', doc_id)
                self.vertices_with_doc_id.add(vertex_id)
        else:
            vertex_id = self.next_vertex_id
            self.vertex_cache[cache_key] = vertex_id
            self.next_vertex_id += 1

            data = {'type': 'entity', 'name': entity.label}

            if entity.uri:
                data['url'] = entity.uri

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
            if e1.uri:
                metadata['url'] = e1.uri
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
