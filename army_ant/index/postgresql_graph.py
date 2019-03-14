#!/usr/bin/env python
#
# postgresql_graph.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import configparser
import itertools
import json
import logging
import math
import os
import re
import signal
import sqlite3
from collections import Counter, OrderedDict, defaultdict
from enum import Enum
from statistics import mean, variance

import igraph
import jpype
import numpy as np
import pandas as pd
import psycopg2
import tensorflow as tf
import tensorflow_ranking as tfr
import yaml
from aiogremlin import Cluster
from aiohttp.client_exceptions import ClientConnectorError
from jpype import (JavaException, JBoolean, JClass, JDouble, JPackage, JString,
                   isJVMStarted, java, shutdownJVM, startJVM)
from sklearn.externals import joblib
from sklearn.preprocessing import MinMaxScaler

from army_ant.exception import ArmyAntException
from army_ant.reader import Document, Entity
from army_ant.setup import config_logger
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.util.text import analyze

logger = logging.getLogger(__name__)


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
                if row[2]:
                    node['properties'] = row[2]
                if row[3]:
                    node['outE'] = row[3]
                if row[4]:
                    node['inE'] = row[4]
                f.write(json.dumps(node) + '\n')

    async def load_to_gremlin_server(self, graphson_path):
        logger.info("Bulk loading to JanusGraph...")
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        result_set = await self.client.submit(
            load_gremlin_script('load_graphson'),
            {'graphsonPath': graphson_path, 'indexPath': self.index_path})
        await result_set.all()

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

        if not pgonly:
            self.postgres_to_graphson(conn, '/tmp/graph.json')

        conn.close()

        if not pgonly:
            await self.load_to_gremlin_server('/tmp/graph.json')
        # yield None
