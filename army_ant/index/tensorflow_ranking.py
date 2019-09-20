#!/usr/bin/env python
#
# tensorflow_ranking.py
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
from jpype import (JException, JBoolean, JClass, JDouble, JPackage,
                   JString, isJVMStarted, java, shutdownJVM, startJVM)
from sklearn.externals import joblib
from sklearn.preprocessing import MinMaxScaler

from army_ant.exception import ArmyAntException
from army_ant.reader import Document, Entity
from army_ant.setup import config_logger
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.util.text import textrank

from . import JavaIndex
from . import LuceneEngine
from . import Result
from . import ResultSet


logger = logging.getLogger(__name__)


class TensorFlowRanking(JavaIndex):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'


    FEATURES = ['num_query_terms', 'norm_num_query_terms', 'idf', 'sum_query_tf', 'min_query_tf', 'max_query_tf',
                'avg_query_tf', 'var_query_tf', 'stream_length', 'sum_norm_tf', 'min_norm_tf', 'max_norm_tf',
                'avg_norm_tf', 'var_norm_tf', 'url_slashes', 'url_length', 'indegree', 'outdegree', 'pagerank',
                'tf_idf', 'bm25', 'lm_jelinek_mercer', 'lm_dirichlet']
    LOSS = 'list_mle_loss'
    LIST_SIZE = 100
    NUM_FEATURES = 136
    BATCH_SIZE = 32
    HIDDEN_LAYER_DIMS = ['20', '10']

    JLearningToRankHelper = JavaIndex.armyant.lucene.LuceneLearningToRankHelper


    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.lucene_index_location = os.path.join(index_location, 'lucene')
        self.index_features = [TensorFlowRanking.Feature[index_feature] for index_feature in index_features]

        lucene_index_features = []
        if TensorFlowRanking.Feature.keywords in self.index_features:
            lucene_index_features.append(LuceneEngine.Feature.keywords.name)

        self.lucene_engine = LuceneEngine(reader, self.lucene_index_location, lucene_index_features, loop)
        self.graph = OrderedDict()
        self.web_features = {}
        self.scaler_filename = os.path.join(index_location, "scaler.pickle")


    def load_topics(self, features_location):
        topics = {}

        with open(os.path.join(features_location, 'topics.txt'), 'r') as f:
            for line in f:
                topic_id, query = line.strip().split('\t')
                topics[topic_id] = query

        return topics


    def load_qrels(self, features_location):
        qrels = defaultdict(lambda: {})

        with open(os.path.join(features_location, 'qrels.txt'), 'r') as f:
            for line in f:
                topic_id, _, doc_id, score = line.strip().split(' ', 4)[:4]
                score = int(score)
                qrels[topic_id][doc_id] = 1 if score > 0 else 0

        return qrels


    def process_web_features(self, doc):
        if not doc.doc_id in self.web_features:
            self.web_features[doc.doc_id] = {}
        self.web_features[doc.doc_id]['url_slashes'] = doc.metadata['url'].count('/')
        self.web_features[doc.doc_id]['url_length'] = len(doc.metadata['url'])
        self.graph[doc.doc_id] = doc.links or []


    def j_build_graph_based_features(self):
        logger.info("Building graph and computing graph-based features")
        self.graph = igraph.Graph.TupleList(
            [(k, v) for k, vs in self.graph.items() for v in vs],
            directed=True)
        indegree = self.graph.indegree()
        outdegree = self.graph.outdegree()
        pagerank = self.graph.pagerank()

        logger.info("Updating Lucene index with web features")
        j_graph_based_features = java.util.HashMap()
        for v in self.graph.vs.select(name_in=self.web_features.keys()):
            j_features = java.util.LinkedHashMap()

            for feature_name, feature_value in self.web_features[v['name']].items():
                j_features.put(feature_name, float(feature_value))

            j_features.put('indegree', float(indegree[v.index]))
            j_features.put('outdegree', float(outdegree[v.index]))
            j_features.put('pagerank', float(pagerank[v.index]))

            j_graph_based_features.put(v['name'], j_features)

        return j_graph_based_features


    def build_train_set(self, ltr_helper, topics, qrels):
        """Compute query features for topics and qrels and prepare the training set."""

        train_set = pd.DataFrame(columns=['label', 'qid', 'doc_id'] + TensorFlowRanking.FEATURES)

        for topic_id, doc_scores in qrels.items():
            query = topics[topic_id]

            j_doc_ids = java.util.ArrayList()
            for doc_id in doc_scores.keys():
                j_doc_ids.add(doc_id)

            j_doc_query_features = ltr_helper.computeQueryDocumentFeatures(query, j_doc_ids)
            for entry in j_doc_query_features.entrySet():
                doc_id = entry.getKey()
                label = float(doc_scores[doc_id])
                j_features = entry.getValue()

                train_set = train_set.append(
                    pd.Series(
                        data=[label, topic_id, doc_id] + [v.floatValue() for v in j_features.values()],
                        index=['label', 'qid', 'doc_id'] + [v for v in j_features.keySet()]),
                    ignore_index=True)

        train_set = train_set.fillna(0)

        logger.info("Scaling features")
        scaler = MinMaxScaler(feature_range=[-1, 1])
        train_set.iloc[:, 3:train_set.shape[1]] = scaler.fit_transform(train_set.iloc[:, 3:train_set.shape[1]])
        joblib.dump(scaler, self.scaler_filename)
        logger.info("Saved scaler to %s" % self.scaler_filename)

        logger.info("Sorting by qid")
        train_set = train_set.sort_values(by=['qid'])

        # train_set.to_csv('/tmp/features.csv')

        return train_set


    def build_predict_set(self, ltr_helper, query, filter_by_doc_id=None):
        """Compute query features for topics and qrels and prepare the training set."""

        if filter_by_doc_id is None:
            j_doc_query_features = ltr_helper.computeQueryDocumentFeatures(query)
        else:
            j_doc_ids = java.util.ArrayList()
            for doc_id in filter_by_doc_id:
                j_doc_ids.add(doc_id)
            j_doc_query_features = ltr_helper.computeQueryDocumentFeatures(query, j_doc_ids)

        doc_ids = []
        predict_set = pd.DataFrame(columns=TensorFlowRanking.FEATURES)

        for entry in j_doc_query_features.entrySet():
            doc_id = entry.getKey()
            j_features = entry.getValue()

            doc_ids.append(doc_id)

            predict_set = predict_set.append(
                pd.Series(
                    data=[v.floatValue() for v in j_features.values()],
                    index=[v for v in j_features.keySet()]),
                ignore_index=True)

        if len(predict_set) != 0:
            logger.info("Scaling features using scaler from %s" % self.scaler_filename)
            scaler = joblib.load(self.scaler_filename)
            predict_set.iloc[:, :] = scaler.fit_transform(predict_set)

            num_docs = predict_set.shape[0]
            predict_set = predict_set.to_dict(orient='list', into=OrderedDict)

            if len(predict_set) < TensorFlowRanking.NUM_FEATURES:
                for k in range(len(predict_set)+1, TensorFlowRanking.NUM_FEATURES+1):
                    predict_set[k] = [0] * num_docs

            predict_set = {str(k): np.array([[d] for d in v], dtype=np.float32)
                           for k, v in enumerate(predict_set.values(), 1)}
        else:
            logger.warning("Prediction set is empty")

        return doc_ids, predict_set


    def pandas_generator(self, dataset):
        num_features = TensorFlowRanking.NUM_FEATURES
        list_size = TensorFlowRanking.LIST_SIZE

        def inner_generator():
            columns = ['label', 'qid', 'doc_id'] + [str(v) for v in range(1, num_features+1)]
            for qid, group in dataset.groupby('qid'):
                x = pd.DataFrame(columns=columns)

                rand_idx = np.random.choice(len(group), min(list_size, len(group)))
                for row in group.iloc[rand_idx, :].values:
                    doc_features = np.pad(row, (0, num_features - len(row) + 3), 'constant', constant_values=(0, 0))
                    x = x.append(pd.Series(data=doc_features, index=columns), ignore_index=True)

                if len(x) < list_size:
                    zeros = pd.DataFrame([[-1] + [0] * (num_features + 2)], columns=columns)
                    x = pd.concat([x] + [zeros] * (list_size - len(x)))

                features = {str(k): np.array([[d] for d in v], dtype=np.float32)
                            for k, v in x.iloc[:, 3:].to_dict('list').items()}
                labels = np.array(x['label'].values, dtype=np.float32)
                if np.any(np.isnan(labels)):
                    labels = None

                yield features, labels

        return inner_generator


    def input_fn(self, pd_generator):
        train_set = tf.data.Dataset.from_generator(
            pd_generator,
            output_types=(
                {str(k): tf.float32 for k in range(1, TensorFlowRanking.NUM_FEATURES + 1)},
                tf.float32
            ),
            output_shapes=(
                {str(k): tf.TensorShape([TensorFlowRanking.LIST_SIZE, 1])
                 for k in range(1, TensorFlowRanking.NUM_FEATURES + 1)},
                tf.TensorShape([TensorFlowRanking.LIST_SIZE])
            )
        )

        train_set = train_set.shuffle(1000).repeat().batch(TensorFlowRanking.BATCH_SIZE)
        return train_set.make_one_shot_iterator().get_next()


    def example_feature_columns(self):
        feature_names = ["%d" % (i + 1) for i in range(0, TensorFlowRanking.NUM_FEATURES)]
        return {name: tf.feature_column.numeric_column(name, shape=(1,), default_value=0.0)
                for name in feature_names}


    def make_score_fn(self):
        def _score_fn(context_features, group_features, mode, params, config):
            del params
            del config
            example_input = [tf.layers.flatten(group_features[name])
                             for name in sorted(self.example_feature_columns())]
            input_layer = tf.concat(example_input, 1)

            cur_layer = input_layer
            for i, layer_width in enumerate(int(d) for d in TensorFlowRanking.HIDDEN_LAYER_DIMS):
                cur_layer = tf.layers.dense(
                    cur_layer,
                    units=layer_width,
                    activation="tanh")

            logits = tf.layers.dense(cur_layer, units=1)
            return logits

        return _score_fn


    def eval_metric_fns(self):
        metric_fns = {}
        metric_fns.update({
            "metric/ndcg@%d" % topn: tfr.metrics.make_ranking_metric_fn(tfr.metrics.RankingMetricKey.NDCG, topn=topn)
            for topn in [1, 3, 5, 10]
        })

        return metric_fns


    def get_estimator(self, hparams):
        def _train_op_fn(loss):
            return tf.contrib.layers.optimize_loss(
                loss=loss,
                global_step=tf.train.get_global_step(),
                learning_rate=hparams.learning_rate,
                optimizer="Adagrad")

        ranking_head = tfr.head.create_ranking_head(
            loss_fn=tfr.losses.make_loss_fn(TensorFlowRanking.LOSS),
            eval_metric_fns=self.eval_metric_fns(),
            train_op_fn=_train_op_fn)

        return tf.estimator.Estimator(
            model_fn=tfr.model.make_groupwise_ranking_fn(
                group_score_fn=self.make_score_fn(),
                group_size=1,
                transform_fn=None,
                ranking_head=ranking_head),
            model_dir=os.path.join(self.index_location, 'model'),
            params=hparams)


    async def index(self, features_location=None):
        if not features_location:
            raise ArmyAntException("Must provide a features location with topics.txt and qrels.txt files")

        topics = self.load_topics(features_location)
        qrels = self.load_qrels(features_location)

        async for doc in self.lucene_engine.index(features_location=features_location):
            self.process_web_features(doc)
            yield doc

        ltr_helper = TensorFlowRanking.JLearningToRankHelper(self.lucene_index_location)
        ltr_helper.computeDocumentFeatures()
        j_graph_based_features = self.j_build_graph_based_features()
        ltr_helper.updateDocumentFeatures(j_graph_based_features)
        train_set = self.build_train_set(ltr_helper, topics, qrels)

        # print(train_set)

        pd_train_generator = self.pandas_generator(train_set)

        logger.info("Training model")
        hparams = tf.contrib.training.HParams(learning_rate=0.05)
        ranker = self.get_estimator(hparams)
        ranker.train(input_fn=lambda: self.input_fn(pd_train_generator), steps=100)


    async def search(self, query, offset, limit, query_type=None, task=None,
                     ranking_function=None, ranking_params=None, debug=False):
        hparams = tf.contrib.training.HParams(learning_rate=0.05)
        ranker = self.get_estimator(hparams)

        k = 1000
        ltr_helper = TensorFlowRanking.JLearningToRankHelper(self.lucene_index_location)
        doc_ids = [result.id for result in ltr_helper.search(
            query, 0, k, task=task, ranking_function=ranking_function, ranking_params=ranking_params, debug=debug)]

        logger.info("Using %d documents for reranking" % len(doc_ids))

        doc_ids, predict_set = self.build_predict_set(ltr_helper, query, filter_by_doc_id=doc_ids)

        # print(predict_set)

        results = ranker.predict(input_fn=lambda: (predict_set, None))
        print(list(results))
        results = zip([next(results)[0] for i in range(k)], doc_ids)
        results = sorted(results, key=lambda d: -d[0])

        results = [Result(score=result[0], id=result[1], name=result[1], type='document')
                   for result in itertools.islice(results, offset, offset + limit)]

        return ResultSet(results, len(doc_ids))
