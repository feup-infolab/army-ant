#!/usr/bin/env python
#
# graph_of_word_csv.py
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

from . import GraphOfWordBatch

logger = logging.getLogger(__name__)


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
