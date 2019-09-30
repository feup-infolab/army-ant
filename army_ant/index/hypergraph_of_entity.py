#!/usr/bin/env python
#
# hypergraph_of_entity.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import itertools
import json
import logging
import os
from enum import Enum

import jpype
from jpype import JClass, JException, JString, java

from army_ant.exception import ArmyAntException
from army_ant.reader import Document
from army_ant.util.text import textrank

from . import Index, JavaIndex, Result, ResultSet

logger = logging.getLogger(__name__)


class HypergraphOfEntity(JavaIndex):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'
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

    class QueryType(Enum):
        keyword = 'KEYWORD_QUERY'
        entity = 'ENTITY_QUERY'

    JHypergraphOfEntityInMemory = JavaIndex.armyant.hgoe.HypergraphOfEntity
    JFeature = JClass("armyant.hgoe.HypergraphOfEntity$Feature")
    JRankingFunction = JClass("armyant.hgoe.HypergraphOfEntity$RankingFunction")
    JTask = JClass("armyant.hgoe.HypergraphOfEntity$Task")
    JQueryType = JClass("armyant.hgoe.HypergraphOfEntity$QueryType")

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.index_features = [HypergraphOfEntity.Feature[index_feature] for index_feature in index_features]

    async def load(self):
        if self.index_location in HypergraphOfEntity.INSTANCES:
            logger.warning("%s is already loaded, skipping" % self.index_location)
            return
        features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value)
                    for index_feature in self.index_features
                    if index_feature != HypergraphOfEntity.Feature.keywords]
        HypergraphOfEntity.INSTANCES[self.index_location] = HypergraphOfEntity.JHypergraphOfEntityInMemory(
            self.index_location, java.util.Arrays.asList(features))
        HypergraphOfEntity.INSTANCES[self.index_location].prepareAutocomplete()

    def ensure_loaded(self):
        if self.index_location not in HypergraphOfEntity.INSTANCES:
            features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value)
                        for index_feature in self.index_features
                        if index_feature != HypergraphOfEntity.Feature.keywords]
            hgoe = HypergraphOfEntity.JHypergraphOfEntityInMemory(
                self.index_location, java.util.Arrays.asList(features))
            hgoe.prepareAutocomplete()
            HypergraphOfEntity.INSTANCES[self.index_location] = hgoe

    async def index(self, features_location=None):
        try:
            if HypergraphOfEntity.Feature.keywords in self.index_features:
                    logger.info("Indexing top %.0f%% keywords per document based on TextRank" % (Index.KW_RATIO * 100))

            index_features_str = ':'.join([index_feature.value for index_feature in self.index_features])
            features = [HypergraphOfEntity.JFeature.valueOf(index_feature.value)
                        for index_feature in self.index_features
                        if index_feature != HypergraphOfEntity.Feature.keywords]

            if HypergraphOfEntity.Feature.context in self.index_features:
                if features_location is None:
                    raise ArmyAntException("Must provide a features_location pointing to a directory")
                if 'word2vec_simnet.graphml.gz' not in os.listdir(features_location):
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

                if HypergraphOfEntity.Feature.keywords in self.index_features:
                    doc.text = textrank(doc.text, ratio=Index.KW_RATIO)

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
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

    async def search(self, query, offset, limit, query_type=None, task=None,
                     base_index_location=None, base_index_type=None,
                     ranking_function=None, ranking_params=None, debug=False):
        if ranking_function:
            try:
                ranking_function = HypergraphOfEntity.RankingFunction[ranking_function]
            except (JException, KeyError):
                logger.error("Could not use '%s' as the ranking function" % ranking_function)
                ranking_function = HypergraphOfEntity.RankingFunction['random_walk']
        else:
            ranking_function = HypergraphOfEntity.RankingFunction['random_walk']

        if query_type:
            if type(query_type) is not Index.QueryType:
                try:
                    query_type = HypergraphOfEntity.QueryType[query_type]
                except (JException, KeyError):
                    logger.error("Could not use '%s' as a query type" % query_type)
                    query_type = HypergraphOfEntity.QueryType['keyword']
        else:
            query_type = HypergraphOfEntity.QueryType['keyword']

        if task:
            if type(task) is not Index.RetrievalTask:
                try:
                    task = Index.RetrievalTask[task]
                except (JException, KeyError):
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
            self.ensure_loaded()
            hgoe = HypergraphOfEntity.INSTANCES[self.index_location]

            task = HypergraphOfEntity.JTask.valueOf(task.value)
            query_type = HypergraphOfEntity.JQueryType.valueOf(query_type.value)
            results = hgoe.search(query, offset, limit, query_type, task, ranking_function, ranking_params, debug)
            num_docs = results.getNumDocs()
            trace = results.getTrace()
            results = [Result(result.getScore(), result.getID(), result.getName(), result.getType())
                       for result in itertools.islice(results, offset, offset + limit)]
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

        return ResultSet(results, num_docs, trace=json.loads(trace.toJSON()), trace_ascii=trace.toASCII())

    async def inspect(self, feature, workdir):
        try:
            self.ensure_loaded()
            hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
            hgoe.inspect(feature, workdir)
        except JException as e:
            logger.error("Java Exception: %s" % e.stacktrace())

    async def autocomplete(self, substring):
        self.ensure_loaded()
        hgoe = HypergraphOfEntity.INSTANCES[self.index_location]
        return [m for m in hgoe.autocomplete(substring)]
