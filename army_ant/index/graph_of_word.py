#!/usr/bin/env python
#
# graph_of_word.py
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

from . import GremlinServerIndex

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

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
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
