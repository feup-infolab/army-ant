#!/usr/bin/env python
#
# lucene_engine.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import json
import logging
import os
from enum import Enum

import jpype
import pandas as pd
from jpype import JClass, JException, JString, java

from army_ant.exception import ArmyAntException
from army_ant.util.text import textrank

from . import JavaIndex, Result, ResultSet

logger = logging.getLogger(__name__)


class LuceneEngine(JavaIndex):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'

    class RankingFunction(Enum):
        tf_idf = 'TF_IDF'
        bm25 = 'BM25'
        dfr = 'DFR'

    JLuceneEngine = JavaIndex.armyant.lucene.LuceneEngine
    JRankingFunction = JClass("armyant.lucene.LuceneEngine$RankingFunction")

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.index_features = [LuceneEngine.Feature[index_feature] for index_feature in index_features]

    async def index(self, features_location=None):
        try:
            if LuceneEngine.Feature.keywords in self.index_features:
                    logger.info("Indexing top %.0f%% keywords per document based on TextRank" %
                                (LuceneEngine.KW_RATIO * 100))

            lucene = LuceneEngine.JLuceneEngine(self.index_location)
            lucene.open()

            corpus = []
            for doc in self.reader:
                logger.debug("Preloading document %s (%d triples)" % (doc.doc_id, len(doc.triples)))

                entities = []
                if doc.entities:
                    for entity in doc.entities:
                        try:
                            entities.append(JavaIndex.JEntity(entity.label, entity.uri))
                        except Exception as e:
                            logger.warning("Entity %s skipped" % entity)
                            logger.exception(e)

                triples = []
                for s, p, o in doc.triples:
                    try:
                        triples.append(
                            JavaIndex.JTriple(
                                JavaIndex.JEntity(s.label, s.uri),
                                JavaIndex.JEntity(p.label, p.uri),
                                JavaIndex.JEntity(o.label, o.uri)))
                    except Exception as e:
                        logger.warning("Triple (%s, %s, %s) skipped" % (s, p, o))
                        logger.exception(e)

                if LuceneEngine.Feature.keywords in self.index_features:
                    doc.text = textrank(doc.text, ratio=LuceneEngine.KW_RATIO)

                jDoc = LuceneEngine.JDocument(
                    JString(doc.doc_id), doc.title, JString(doc.text), java.util.Arrays.asList(triples),
                    java.util.Arrays.asList(entities))
                corpus.append(jDoc)
                if len(corpus) % (LuceneEngine.BLOCK_SIZE // 10) == 0:
                    logger.info("%d documents preloaded" % len(corpus))

                if len(corpus) >= LuceneEngine.BLOCK_SIZE:
                    logger.info("Indexing batch of %d documents" % len(corpus))
                    lucene.indexCorpus(java.util.Arrays.asList(corpus))
                    corpus = []

                # yield Document(
                #     doc_id=doc.doc_id,
                #     metadata={
                #         'url': doc.metadata.get('url'),
                #         'name': doc.metadata.get('name')
                #     })
                yield doc

            if len(corpus) > 0:
                logger.info("Indexing batch of %d documents" % len(corpus))
                lucene.indexCorpus(java.util.Arrays.asList(corpus))

            lucene.close()
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

    async def search(self, query, offset, limit, query_type=None, task=None,
                     base_index_location=None, base_index_type=None,
                     ranking_function=None, ranking_params=None, debug=False):
        if ranking_function:
            try:
                ranking_function = LuceneEngine.RankingFunction[ranking_function]
            except (JException, KeyError):
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
            if self.index_location in LuceneEngine.INSTANCES:
                lucene = LuceneEngine.INSTANCES[self.index_location]
            else:
                lucene = LuceneEngine.JLuceneEngine(self.index_location)
                LuceneEngine.INSTANCES[self.index_location] = lucene

            results = lucene.search(query, offset, limit, ranking_function, ranking_params)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in results]
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())


class LuceneFeaturesEngine(JavaIndex):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'

    JFeaturesHelper = JavaIndex.armyant.lucene.LuceneFeaturesHelper

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.lucene_index_location = os.path.join(index_location, 'lucene')
        self.index_features = [LuceneFeaturesEngine.Feature[index_feature] for index_feature in index_features]

        lucene_index_features = []
        if LuceneFeaturesEngine.Feature.keywords in self.index_features:
            lucene_index_features.append(LuceneEngine.Feature.keywords.name)

        self.lucene_engine = LuceneEngine(reader, self.lucene_index_location, lucene_index_features, loop)

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

    async def search(self, query, offset, limit, query_type=None, task=None,
                     base_index_location=None, base_index_type=None,
                     ranking_function=None, ranking_params=None, debug=False):
        if ranking_function:
            try:
                ranking_function = LuceneEngine.RankingFunction[ranking_function]
            except (JException, KeyError):
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
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())
