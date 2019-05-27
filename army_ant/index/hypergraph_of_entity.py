#!/usr/bin/env python
#
# hypergraph_of_entity.py
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

from . import Index
from . import JavaIndex
from . import Result
from . import ResultSet

logger = logging.getLogger(__name__)


class HypergraphOfEntity(JavaIndex):
    class Feature(Enum):
        sents = 'SENTENCES'
        syns = 'SYNONYMS'
        context = 'CONTEXT'
        weight = 'WEIGHT'
        prune = 'PRUNE'
        skip_related_to = 'SKIP_RELATED_TO'
        related_to_by_doc = 'RELATED_TO_BY_DOC'
        related_to_by_subj = 'RELATED_TO_BY_SUBJ'

    class RankingFunction(Enum):
        entity_weight = 'ENTITY_WEIGHT'
        jaccard = 'JACCARD_SCORE'
        random_walk = 'RANDOM_WALK_SCORE'
        biased_random_walk = 'BIASED_RANDOM_WALK_SCORE'
        undirected_random_walk = 'UNDIRECTED_RANDOM_WALK_SCORE'
        random_walk_without_seeds = 'RANDOM_WALK_SCORE_WITHOUT_SEEDS'
        biased_random_walk_without_seeds = 'BIASED_RANDOM_WALK_SCORE_WITHOUT_SEEDS'
        hyperrank = 'HYPERRANK'

    JHypergraphOfEntityInMemory = JavaIndex.armyant.hgoe.HypergraphOfEntity
    JFeature = JClass("armyant.hgoe.HypergraphOfEntity$Feature")
    JRankingFunction = JClass("armyant.hgoe.HypergraphOfEntity$RankingFunction")
    JTask = JClass("armyant.hgoe.HypergraphOfEntity$Task")

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.index_features = [HypergraphOfEntity.Feature[index_feature] for index_feature in index_features]

    async def load(self):
        if self.index_location in JavaIndex.INSTANCES:
            logger.warning("%s is already loaded, skipping" % self.index_location)
            return
        features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                    self.index_features]
        JavaIndex.INSTANCES[self.index_location] = HypergraphOfEntity.JHypergraphOfEntityInMemory(
            self.index_location, java.util.Arrays.asList(features))

    async def index(self, features_location=None):
        try:
            index_features_str = ':'.join([index_feature.value for index_feature in self.index_features])
            features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value)
                        for index_feature in self.index_features]

            if HypergraphOfEntity.Feature.context in self.index_features:
                if features_location is None:
                    raise ArmyAntException("Must provide a features_location pointing to a directory")
                if not 'word2vec_simnet.graphml.gz' in os.listdir(features_location):
                    raise ArmyAntException(
                        "Must provide a 'word2vec_simnet.graphml.gz' file within features directory")

            hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                self.index_location, java.util.Arrays.asList(features), features_location, True)

            corpus = []
            for doc in self.reader:
                logger.debug("Preloading document %s (%d triples)" % (doc.doc_id, len(doc.triples)))

                entities = []
                if doc.entities:
                    for entity in doc.entities:
                        try:
                            entities.append(HypergraphOfEntity.JEntity(entity.label, entity.uri))
                        except Exception as e:
                            logger.warning("Entity %s skipped" % entity)
                            logger.exception(e)

                triples = []
                for s, p, o in doc.triples:
                    try:
                        triples.append(
                            HypergraphOfEntity.JTriple(
                                HypergraphOfEntity.JEntity(s.label, s.uri),
                                HypergraphOfEntity.JEntity(p.label, p.uri),
                                HypergraphOfEntity.JEntity(o.label, o.uri)))
                    except Exception as e:
                        logger.warning("Triple (%s, %s, %s) skipped" % (s, p, o))
                        logger.exception(e)

                jDoc = HypergraphOfEntity.JDocument(
                    JString(doc.doc_id), doc.title, JString(doc.text), java.util.Arrays.asList(triples),
                    java.util.Arrays.asList(entities))
                corpus.append(jDoc)

                if len(corpus) % (JavaIndex.BLOCK_SIZE // 10) == 0:
                    logger.info("%d documents preloaded" % len(corpus))

                if len(corpus) >= JavaIndex.BLOCK_SIZE:
                    logger.info("Indexing batch of %d documents using %s" % (len(corpus), index_features_str))
                    hgoe.indexCorpus(java.util.Arrays.asList(corpus))
                    corpus = []

                yield Document(
                    doc_id=doc.doc_id,
                    metadata={
                        'url': doc.metadata.get('url'),
                        'name': doc.metadata.get('name')
                    })

            if len(corpus) > 0:
                logger.info("Indexing batch of %d documents using %s" % (len(corpus), index_features_str))
                hgoe.indexCorpus(java.util.Arrays.asList(corpus))

            hgoe.postProcessing()

            hgoe.save()
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        if ranking_function:
            try:
                ranking_function = HypergraphOfEntity.RankingFunction[ranking_function]
            except (JavaException, KeyError) as e:
                logger.error("Could not use '%s' as the ranking function" % ranking_function)
                ranking_function = HypergraphOfEntity.RankingFunction['random_walk']
        else:
            ranking_function = HypergraphOfEntity.RankingFunction['random_walk']

        if task:
            if not type(task) is Index.RetrievalTask:
                try:
                    task = Index.RetrievalTask[task]
                except (JavaException, KeyError) as e:
                    logger.error("Could not use '%s' as the ranking function" % ranking_function)
                    task = Index.RetrievalTask['document_retrieval']
        else:
            task = Index.RetrievalTask['document_retrieval']

        logger.info("Using '%s' as ranking function" % ranking_function.value)
        ranking_function = HypergraphOfEntity.JRankingFunction.valueOf(ranking_function.value)

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
            if self.index_location in HypergraphOfEntity.INSTANCES:
                hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            else:
                features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                            self.index_features]
                hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                    self.index_location, java.util.Arrays.asList(features))
                HypergraphOfEntity.INSTANCES[self.index_location] = hgoe

            task = HypergraphOfEntity.JTask.valueOf(task.value)
            results = hgoe.search(query, offset, limit, task, ranking_function, ranking_params, debug)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in itertools.islice(results, offset, offset + limit)]
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())

    async def inspect(self, feature, workdir):
        try:
            if self.index_location in HypergraphOfEntity.INSTANCES:
                hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            else:
                features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value) for index_feature in
                            self.index_features]
                hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                    self.index_location, java.util.Arrays.asList(features))
                HypergraphOfEntity.INSTANCES[self.index_location] = hgoe

            hgoe.inspect(feature, workdir)
        except JavaException as e:
            logger.error("Java Exception: %s" % e.stacktrace())
