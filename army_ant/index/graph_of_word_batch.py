#!/usr/bin/env python
#
# graph_of_word_batch.py
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

from . import PostgreSQLGraph
from . import GraphOfWord

logger = logging.getLogger(__name__)


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
