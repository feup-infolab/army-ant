#!/usr/bin/env python
#
# index.py
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


class Index(object):
    PRELOADED = {}

    class RetrievalTask(Enum):
        document_retrieval = 'DOCUMENT_RETRIEVAL'
        entity_retrieval = 'ENTITY_RETRIEVAL'
        term_retrieval = 'TERM_RETRIEVAL'

    @staticmethod
    def __preloaded_key__(index_location, index_type):
        return '%s::%s' % (index_location, index_type)

    @staticmethod
    def factory(reader, index_location, index_type, loop):
        import army_ant.index as idx

        if index_type == 'gow':
            return idx.GraphOfWord(reader, index_location, loop)
        elif index_type == 'goe':
            return idx.GraphOfEntity(reader, index_location, loop)
        elif index_type == 'gow_batch':
            return idx.GraphOfWordBatch(reader, index_location, loop)
        elif index_type == 'goe_batch':
            return idx.GraphOfEntityBatch(reader, index_location, loop)
        elif index_type == 'gow_csv':
            return idx.GraphOfWordCSV(reader, index_location, loop)
        elif index_type == 'goe_csv':
            return idx.GraphOfEntityCSV(reader, index_location, loop)
        elif index_type.startswith('hgoe'):
            index_features = index_type.split(':')[1:]
            return idx.HypergraphOfEntity(reader, index_location, index_features, loop)
        elif index_type == 'lucene':
            return idx.LuceneEngine(reader, index_location, loop)
        elif index_type == 'tfr':
            return idx.TensorFlowRanking(reader, index_location, loop)
        elif index_type == 'lucene_features':
            return idx.LuceneFeaturesEngine(reader, index_location, loop)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    @staticmethod
    def open(index_location, index_type, loop):
        import army_ant.index as idx

        key = Index.__preloaded_key__(index_location, index_type)
        if key in Index.PRELOADED:
            return Index.PRELOADED[key]

        if index_type == 'gow':
            return idx.GraphOfWord(None, index_location, loop)
        elif index_type == 'goe':
            return idx.GraphOfEntity(None, index_location, loop)
        elif index_type == 'gow_batch':
            return idx.GraphOfWordBatch(None, index_location, loop)
        elif index_type == 'goe_batch':
            return idx.GraphOfEntityBatch(None, index_location, loop)
        elif index_type == 'gow_csv':
            return idx.GraphOfWordCSV(None, index_location, loop)
        elif index_type == 'goe_csv':
            return idx.GraphOfEntityCSV(None, index_location, loop)
        elif index_type == 'gremlin':
            return idx.GremlinServerIndex(None, index_location, loop)
        elif index_type.startswith('hgoe'):
            index_features = index_type.split(':')[1:]
            return idx.HypergraphOfEntity(None, index_location, index_features, loop)
        elif index_type == 'lucene':
            return idx.LuceneEngine(None, index_location, loop)
        elif index_type == 'tfr':
            return idx.TensorFlowRanking(None, index_location, loop)
        elif index_type == 'lucene_features':
            return idx.LuceneFeaturesEngine(None, index_location, loop)
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
        async for _ in index:
            pass

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

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        raise ArmyAntException("Search not implemented for %s" % self.__class__.__name__)

    async def inspect(self, feature, workdir='.'):
        raise ArmyAntException("Inspect not implemented for %s" % self.__class__.__name__)
