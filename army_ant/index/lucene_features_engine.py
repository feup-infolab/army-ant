#!/usr/bin/env python
#
# lucene_features_engine.py
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

from . import JavaIndex
from . import LuceneEngine

logger = logging.getLogger(__name__)


class LuceneFeaturesEngine(JavaIndex):
    JFeaturesHelper = JavaIndex.armyant.lucene.LuceneFeaturesHelper

    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.lucene_index_location = os.path.join(index_location, 'lucene')
        self.lucene_engine = LuceneEngine(reader, self.lucene_index_location, loop)

    def j_load_features(self, features_location):
        logger.info("Loading query-independent features from %s" % features_location)
        features = pd.read_csv(os.path.join(features_location, 'features.csv'))

        j_features = java.util.HashMap()
        for _, row in features.iterrows():
            j_doc_features = java.util.LinkedHashMap()

            for feature_name, feature_value in row.drop('id').iteritems():
                j_doc_features.put(feature_name, float(feature_value))

            j_features.put(row.id, j_doc_features)

        return j_features

    async def index(self, features_location=None):
        if not features_location:
            raise ArmyAntException("Must provide a features location with topics.txt and qrels.txt files")

        async for doc in self.lucene_engine.index(features_location=features_location):
            yield doc

        features_helper = LuceneFeaturesEngine.JFeaturesHelper(self.lucene_index_location)
        j_features = self.j_load_features(features_location)
        features_helper.setDocumentFeatures(j_features)

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
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
            features_helper = LuceneFeaturesEngine.JFeaturesHelper(self.lucene_index_location)

            results = features_helper.search(query, offset, limit, ranking_function, ranking_params)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in results]
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())
