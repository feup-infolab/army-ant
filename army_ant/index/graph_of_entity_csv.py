#!/usr/bin/env python
#
# graph_of_entity_csv.py
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

from . import GraphOfEntityBatch

logger = logging.getLogger(__name__)


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
