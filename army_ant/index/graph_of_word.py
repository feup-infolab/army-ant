#!/usr/bin/env python
#
# graph_of_word.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging
import os

import psycopg2
from aiogremlin import Cluster
from aiohttp.client_exceptions import ClientConnectorError

from army_ant.exception import ArmyAntException
from army_ant.index import GremlinServerIndex, PostgreSQLGraph
from army_ant.util import load_gremlin_script

logger = logging.getLogger(__name__)


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

    async def search(self, query, offset, limit, query_type=None, task=None,
                     ranking_function=None, ranking_params=None, debug=False):
        try:
            self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        except ClientConnectorError:
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
            c.copy_expert(
                """COPY (SELECT node_id AS "node_id:ID", attributes->'name'->0->>'value' AS name, """
                """label AS ":LABEL" FROM nodes) TO STDOUT WITH CSV HEADER""", f)

        logging.info("Creating in_window_of edges CSV file")
        with open(os.path.join(self.index_location, 'in_window_of-edges.csv'), 'w') as f:
            c.copy_expert(
                """COPY (SELECT source_node_id AS ":START_ID", attributes->>'doc_id' AS doc_id, """
                """target_node_id AS ":END_ID", label AS ":TYPE" FROM edges) TO STDOUT WITH CSV HEADER""", f)
