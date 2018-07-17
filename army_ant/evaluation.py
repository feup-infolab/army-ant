#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# evaluation.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-19

import asyncio
import csv
import itertools
import json
import logging
import math
import os
import pickle
import re
import shutil
import tempfile
import time
import zipfile
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from enum import IntEnum
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import pymongo
import requests
import requests_cache
from bson.objectid import ObjectId
from lxml import etree
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from army_ant.exception import ArmyAntException
from army_ant.index import Index
from army_ant.util import md5, get_first, zipdir, safe_div
from army_ant.util import ranking_params_to_params_id, params_id_to_str, params_id_to_ranking_params
from army_ant.util.stats import gmean

logger = logging.getLogger(__name__)

#
# TODO FIXME REQUIRES CRITICAL AND MASSIVE REFACTORING!
# Evaluation metrics should be calculated in separate functions and reused by all evaluators.
#

class Evaluator(object):
    @staticmethod
    def factory(task, eval_location):
        if task.eval_format == 'inex':
            return INEXEvaluator(task, eval_location, Index.RetrievalTask.document_retrieval)
        if task.eval_format == 'inex-xer':
            return INEXEvaluator(task, eval_location, Index.RetrievalTask.entity_retrieval)
        if task.eval_format == 'trec':
            return TRECEvaluator(task, eval_location)
        elif task.eval_format == 'll-api':
            return LivingLabsEvaluator(task, eval_location)
        else:
            raise ArmyAntException("Unsupported evaluator format")

    def __init__(self, task, eval_location):
        self.task = task
        self.results = {}
        self.stats = {}
        self.interrupt = False
        self.start_date = datetime.now()

    async def run(self):
        raise ArmyAntException("Unsupported evaluator format %s" % self.task.eval_format)


class FilesystemEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.o_results_path = os.path.join(eval_location, 'results', task._id)
        self.o_assessments_path = os.path.join(eval_location, 'assessments', task._id)

        try:
            os.makedirs(self.o_results_path)
        except FileExistsError:
            raise ArmyAntException("Results directory '%s' already exists" % self.o_results_path)

        try:
            os.makedirs(self.o_assessments_path)
        except FileExistsError:
            raise ArmyAntException("Assessments directory '%s' already exists" % self.o_assessments_path)

    def remove_output(self):
        shutil.rmtree(self.o_results_path, ignore_errors=True)
        shutil.rmtree(self.o_assessments_path, ignore_errors=True)


class TRECEvaluator(FilesystemEvaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)

    async def get_topic_results(self, ranking_params=None, topic_filter=None):
        data = open(self.task.topics_path, 'r').read()

        topics = re.findall(
            r'<top>.*?<num>.*?Number:.*?(\d+).*?<title>.*?([^<]+).*?</top>',
            data, re.MULTILINE | re.DOTALL)

        topics = [(topic_id.strip(), query.strip()) for topic_id, query in topics]

        params_id = ranking_params_to_params_id(ranking_params)

        o_results_path = os.path.join(self.o_results_path, params_id)
        if not os.path.exists(o_results_path): os.makedirs(o_results_path)

        if not params_id in self.stats:
            self.stats[params_id] = {'ranking_params': ranking_params, 'query_time': {}}

        with open(os.path.join(o_results_path, '%s.res' % self.task.run_id), 'w') as trec_f:
            for topic_id, query in topics:
                if self.interrupt:
                    logger.warning("Evaluation task was interruped")
                    break

                if topic_filter and not topic_id in topic_filter:
                    logger.warning("Skipping topic '%s'" % topic_id)
                    continue

                logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (
                    query, topic_id, self.task.index_type, self.task.index_location))
                start_time = time.time()
                engine_response = await self.index.search(
                    query, 0, 10000, Index.RetrievalTask.document_retrieval, self.task.ranking_function, ranking_params)
                end_time = int(round((time.time() - start_time) * 1000))
                self.stats[params_id]['query_time'][topic_id] = end_time

                with open(os.path.join(o_results_path, '%s.csv' % topic_id), 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['rank', 'score', 'doc_id']) # TODO add relevant column from qrels
                    for i, result in zip(range(1, len(engine_response['results']) + 1), engine_response['results']):
                        doc_id = result['id']
                        score = result['score']
                        trec_f.write("%s Q0 %s %s %s %s\n" % (topic_id, doc_id, i, score, self.task.run_id))
                        writer.writerow([i, score, doc_id])

        self.stats[params_id]['total_query_time'] = sum([t for t in self.stats[params_id]['query_time'].values()])
        self.stats[params_id]['avg_query_time'] = (
                self.stats[params_id]['total_query_time'] / len(self.stats[params_id]['query_time']))

    async def run_with_params(self, ranking_params=None):
        await self.get_topic_results(ranking_params=ranking_params)

    async def run(self):
        if self.task.ranking_params:
            sorted_ranking_params = OrderedDict(sorted(self.task.ranking_params.items(), key=lambda d: d[0]))
            keys = list(sorted_ranking_params.keys())
            values = list(sorted_ranking_params.values())

            for param_values in itertools.product(*values):
                ranking_params = dict(zip(keys, param_values))
                await self.run_with_params(ranking_params)
        else:
            await self.run_with_params()


class INEXEvaluator(FilesystemEvaluator):
    def __init__(self, task, eval_location, retrieval_task):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)
        self.retrieval_task = retrieval_task

    def path_to_topic_id(self, path):
        return os.path.basename(os.path.splitext(path)[0])

    def get_topic_assessments(self):
        logger.info("Loading topic assessments")

        topic_doc_judgements = {}

        if not os.path.exists(self.task.assessments_path):
            raise ArmyAntException("Topic assessments file not found: %s" % self.task.assessments_path)

        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                if self.retrieval_task == Index.RetrievalTask.entity_retrieval:
                    topic_id, _, id, _, judgement = line.split(' ', 4)
                else:
                    topic_id, _, id, judgement, _ = line.split(' ', 4)

                if not topic_id in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][id] = int(judgement)

        return topic_doc_judgements

    def get_valid_ids(self):
        if self.task.valid_ids_path and os.path.exists(self.task.valid_ids_path):
            logger.info("Loading valid IDs to filter results")
            valid_ids = set([])

            with open(self.task.valid_ids_path, 'r') as f:
                for line in f:
                    valid_ids.add(line.strip())

            return valid_ids

    async def get_topic_results(self, ranking_params=None, topic_filter=None):
        topic_doc_judgements = self.get_topic_assessments()
        valid_ids = self.get_valid_ids()

        topics = etree.parse(self.task.topics_path)

        params_id = ranking_params_to_params_id(ranking_params)

        o_results_path = os.path.join(self.o_results_path, params_id)
        if not os.path.exists(o_results_path): os.makedirs(o_results_path)

        if self.retrieval_task == Index.RetrievalTask.entity_retrieval:
            xpath_topic = '//inex_topic'
            xpath_topic_id = '@topic_id'
        else:
            xpath_topic = '//topic'
            xpath_topic_id = '@id'

        if not params_id in self.stats:
            self.stats[params_id] = {'ranking_params': ranking_params, 'query_time': {}}

        for topic in topics.xpath(xpath_topic):
            if self.interrupt:
                logger.warning("Evaluation task was interruped")
                break

            topic_id = get_first(topic.xpath(xpath_topic_id))

            if topic_filter and not topic_id in topic_filter:
                logger.warning("Skipping topic '%s'" % topic_id)
                continue

            query = get_first(topic.xpath('title/text()'))
            if self.retrieval_task == Index.RetrievalTask.entity_retrieval:
                categories = topic.xpath('categories/category/text()')
                query += ' %s' % ' '.join(categories)

            logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (
                query, topic_id, self.task.index_type, self.task.index_location))
            start_time = time.time()
            engine_response = await self.index.search(
                query, 0, 10000, self.retrieval_task, self.task.ranking_function, ranking_params)
            end_time = int(round((time.time() - start_time) * 1000))
            self.stats[params_id]['query_time'][topic_id] = end_time

            results = engine_response['results']
            if valid_ids:
                logger.info("Filtering results (only %d IDs are valid)" % (len(valid_ids)))
                results = [result for result in results if result['id'] in valid_ids]

            with open(os.path.join(o_results_path, '%s.csv' % topic_id), 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['rank', 'score', 'doc_id', 'relevant'])
                for i, result in zip(range(1, len(results) + 1), results):
                    doc_id = result['id']
                    score = result['score']
                    relevant = topic_doc_judgements[topic_id][doc_id] > 0 if doc_id in topic_doc_judgements[
                        topic_id] else False
                    writer.writerow([i, score, doc_id, relevant])

        self.stats[params_id]['total_query_time'] = sum([t for t in self.stats[params_id]['query_time'].values()])
        self.stats[params_id]['avg_query_time'] = (
                self.stats[params_id]['total_query_time'] / len(self.stats[params_id]['query_time']))

    def f_score(self, precision, recall, beta=1):
        if precision == 0 and recall == 0: return 0
        return safe_div((1 + beta ** 2) * (precision * recall), (beta ** 2 * precision) + recall)

    def calculate_precision_recall(self, ranking_params=None):
        # topic_id -> doc_id -> num_relevant_chars
        topic_doc_judgements = self.get_topic_assessments()

        params_id = ranking_params_to_params_id(ranking_params)
        o_results_path = os.path.join(self.o_results_path, params_id)

        result_files = [
            os.path.join(o_results_path, f)
            for f in os.listdir(o_results_path)
            if os.path.isfile(os.path.join(o_results_path, f))]

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir): os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'precision_recall_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'tp', 'fp', 'tn', 'fn', 'precision', 'recall', 'f0.5', 'f1', 'f2'])

            tps = []
            fps = []
            tns = []
            fns = []
            precisions = []
            recalls = []
            f_0_5_scores = []
            f_1_scores = []
            f_2_scores = []

            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    result_doc_ids = set([row['doc_id'] for row in reader])

                    tp = fp = tn = fn = 0

                    for doc_id, judgment in topic_doc_judgements.get(topic_id, {}).items():
                        relevant = judgment > 0
                        if relevant:
                            if doc_id in result_doc_ids:
                                tp += 1
                            else:
                                fn += 1
                        else:
                            if doc_id in result_doc_ids:
                                fp += 1
                            else:
                                tn += 1

                    tps.append(tp)
                    fps.append(fp)
                    tns.append(tn)
                    fns.append(fn)

                    logger.debug(
                        "%s - TP(%d) + FP(%d) + TN(%d) + FN(%d) = %d" % (topic_id, tp, fp, tn, fn, tp + fp + tn + fn))

                    precision = safe_div(tp, tp + fp)
                    precisions.append(precision)

                    recall = safe_div(tp, tp + fn)
                    recalls.append(recall)

                    f_0_5_score = self.f_score(precision, recall, beta=0.5)
                    f_0_5_scores.append(f_0_5_score)

                    f_1_score = self.f_score(precision, recall, beta=1)
                    f_1_scores.append(f_1_score)

                    f_2_score = self.f_score(precision, recall, beta=2)
                    f_2_scores.append(f_2_score)

                    writer.writerow([topic_id, tp, fp, tn, fn, precision, recall, f_0_5_score, f_1_score, f_2_score])

            if not params_id in self.results: self.results[params_id] = {'ranking_params': ranking_params,
                                                                         'metrics': {}}
            self.results[params_id]['metrics']['Micro Avg Prec'] = safe_div(sum(tps), sum(tps) + sum(fps))
            self.results[params_id]['metrics']['Micro Avg Rec'] = safe_div(sum(tps), sum(tps) + sum(fns))
            self.results[params_id]['metrics']['Macro Avg Prec'] = safe_div(sum(precisions), len(precisions))
            self.results[params_id]['metrics']['Macro Avg Rec'] = safe_div(sum(recalls), len(recalls))

            self.results[params_id]['metrics']['Micro Avg F0_5'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=0.5)
            self.results[params_id]['metrics']['Micro Avg F1'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=1)
            self.results[params_id]['metrics']['Micro Avg F2'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=2)

            self.results[params_id]['metrics']['Macro Avg F0_5'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=0.5)
            self.results[params_id]['metrics']['Macro Avg F1'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=1)
            self.results[params_id]['metrics']['Macro Avg F2'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=2)

    def calculate_precision_at_n(self, n=10, ranking_params=None):
        params_id = ranking_params_to_params_id(ranking_params)
        o_results_path = os.path.join(self.o_results_path, params_id)

        result_files = [
            os.path.join(o_results_path, f)
            for f in os.listdir(o_results_path)
            if os.path.isfile(os.path.join(o_results_path, f))]

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir): os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'p_at_%d-precision_at_%d_per_topic.csv' % (n, n))

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'p_at_%d' % n])

            precisions_at_n = []
            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in itertools.islice(reader, n):
                        results.append(row['relevant'] == 'True')

                    precision_at_n = results.count(True) / n
                    precisions_at_n.append(precision_at_n)
                    writer.writerow([topic_id, precision_at_n])

            if not params_id in self.results: self.results[params_id] = {'ranking_params': ranking_params,
                                                                         'metrics': {}}
            self.results[params_id]['metrics']['P@%d' % n] = safe_div(sum(precisions_at_n), len(precisions_at_n))

    def calculate_mean_average_precision(self, ranking_params=None):
        params_id = ranking_params_to_params_id(ranking_params)
        o_results_path = os.path.join(self.o_results_path, params_id)

        result_files = [
            os.path.join(o_results_path, f)
            for f in os.listdir(o_results_path)
            if os.path.isfile(os.path.join(o_results_path, f))]

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir): os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'map_average_precision_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'avg_precision'])

            avg_precisions = []
            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                precisions = []
                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in reader:
                        results.append(row['relevant'] == 'True')

                    for i in range(1, len(results) + 1):
                        rel = results[0:i]
                        p = safe_div(sum(rel), len(rel))
                        precisions.append(p)

                    avg_precision = safe_div(sum(precisions), len(precisions))
                    avg_precisions.append(avg_precision)
                    writer.writerow([topic_id, avg_precision])

            if not params_id in self.results: self.results[params_id] = {'ranking_params': ranking_params,
                                                                         'metrics': {}}
            self.results[params_id]['metrics']['MAP'] = safe_div(sum(avg_precisions), len(avg_precisions))
            # This is an approximation of np.prod(avg_precision)**(1/len(avg_precision)) that works with zero values.
            self.results[params_id]['metrics']['GMAP'] = gmean(avg_precisions)

    def calculate_normalized_discounted_cumulative_gain_at_p(self, p=10, ranking_params=None):
        params_id = ranking_params_to_params_id(ranking_params)
        o_results_path = os.path.join(self.o_results_path, params_id)

        result_files = [
            os.path.join(o_results_path, f)
            for f in os.listdir(o_results_path)
            if os.path.isfile(os.path.join(o_results_path, f))]

        ndcgs = []
        for result_file in result_files:
            dcg_parcels = []
            idcg_parcels = []

            with open(result_file, 'r') as rf:
                reader = csv.DictReader(rf)
                results = []
                for row in reader:
                    results.append(row['relevant'] == 'True')

                for i in range(1, min(len(results), p) + 1):
                    rel = results[i - 1]
                    dcg_p = rel / math.log2(i + 1)
                    dcg_parcels.append(dcg_p)

                for i in range(1, len(results) + 1):
                    rel = results[i - 1]
                    idcg_p = (2 ** rel - 1) / math.log2(i + 1)
                    idcg_parcels.append(idcg_p)

                ndcg = safe_div(sum(dcg_parcels), len(idcg_parcels))
                ndcgs.append(ndcg)

        if not params_id in self.results: self.results[params_id] = {'ranking_params': ranking_params, 'metrics': {}}
        self.results[params_id]['metrics']['NDCG@%d' % p] = safe_div(sum(ndcgs), len(ndcgs))

    async def run_with_params(self, ranking_params=None):
        await self.get_topic_results(ranking_params=ranking_params)

        self.calculate_precision_recall(ranking_params=ranking_params)

        self.calculate_precision_at_n(n=10, ranking_params=ranking_params)
        self.calculate_precision_at_n(n=100, ranking_params=ranking_params)
        self.calculate_precision_at_n(n=1000, ranking_params=ranking_params)

        self.calculate_mean_average_precision(ranking_params=ranking_params)

        self.calculate_normalized_discounted_cumulative_gain_at_p(p=10, ranking_params=ranking_params)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=100, ranking_params=ranking_params)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=1000, ranking_params=ranking_params)

    async def run(self):
        if self.task.ranking_params:
            sorted_ranking_params = OrderedDict(sorted(self.task.ranking_params.items(), key=lambda d: d[0]))
            keys = list(sorted_ranking_params.keys())
            values = list(sorted_ranking_params.values())

            for param_values in itertools.product(*values):
                ranking_params = dict(zip(keys, param_values))
                await self.run_with_params(ranking_params)
        else:
            await self.run_with_params()


class LivingLabsEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)
        try:
            base_url, api_key, run_id = eval_location.split('::')
        except ValueError:
            raise ArmyAntException("Must provide the base_url, api_key and run_id, separated by '::'")

        self.base_url = urljoin(base_url, 'api/v2/participant/')
        self.auth = HTTPBasicAuth(api_key, '')
        self.headers = {'Content-Type': 'application/json'}

        requests_cache.install_cache('living_labs_cache', expire_after=10800)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(task.index_location, task.index_type, self.loop)

        self.run_id = run_id
        self.pickle_dir = '/opt/army-ant/cache/%s' % run_id
        if not os.path.exists(self.pickle_dir):
            os.mkdir(self.pickle_dir)

    def get_queries(self, qtype=None, qfilter=None):
        logging.info("Retrieving Living Labs queries")

        r = requests.get(urljoin(self.base_url, 'query'), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        queries = r.json()['queries']

        if qtype: queries = list(filter(lambda q: q['type'] == qtype, queries))
        if qfilter: queries = list(filter(lambda q: q['qid'] in qfilter, queries))

        return queries

    def get_doclist_doc_ids(self, qid):
        logging.info("Retrieving Living Labs doclist for qid=%s" % qid)

        r = requests.get(urljoin(self.base_url, 'doclist/%s' % qid), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        doc_ids = [doc['docid'] for doc in r.json()['doclist']]

        return set(doc_ids)

    def put_run(self, qid, runid, results):
        logging.info("Submitting Living Labs run for qid=%s and runid=%s" % (qid, runid))

        must_have_doc_ids = self.get_doclist_doc_ids(qid)

        # this first verification is required because an empty results variable is returned as a dictionary instead of a list
        if len(results) < 1:
            logging.warn("No results found, adding %d missing results with zero score" % len(must_have_doc_ids))
            results = [{'docID': doc_id} for doc_id in must_have_doc_ids]
        else:
            doc_ids = [result['docID'] for result in results]
            missing_doc_ids = must_have_doc_ids.difference(doc_ids)
            if len(missing_doc_ids) > 0:
                logging.warn("Adding %d missing results with zero score out of %d must have results" % (
                    len(missing_doc_ids), len(must_have_doc_ids)))
                results.extend([{'docID': doc_id} for doc_id in missing_doc_ids])
        data = {
            'qid': qid,
            'runid': runid,
            'doclist': [{'docid': result['docID']} for result in results]
        }

        r = requests.put(urljoin(self.base_url, 'run/%s' % qid), data=json.dumps(data), headers=self.headers,
                         auth=self.auth)
        if r.status_code == requests.codes.conflict:
            logger.warning("Run for qid=%s and runid=%s already exists, ignoring" % (qid, runid))
        else:
            r.raise_for_status()

    async def run(self):
        queries = self.get_queries()
        try:
            for query in queries:
                if self.interrupt:
                    logger.warning("Evaluation task was interrupted")
                    break

                logging.info("Searching for %s (qid=%s)" % (query['qstr'], query['qid']))

                pickle_path = os.path.join(self.pickle_dir, '%s.pickle' % query['qid'])
                if os.path.exists(pickle_path):
                    with open(pickle_path, 'rb') as f:
                        results = pickle.load(f)
                else:
                    engine_response = await self.index.search(
                        query['qstr'], 0, 10000, Index.RetrievalTask.document_retrieval,
                        self.task.ranking_function, self.task.ranking_params)
                    results = engine_response['results']
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(results, f)

                logger.info("%d results found for %s (qid=%s)" % (len(results), query['qstr'], query['qid']))
                self.put_run(query['qid'], self.run_id, results)

            return EvaluationTaskStatus.SUBMITTED
        except HTTPError as e:
            logger.error(e)
            return EvaluationTaskStatus.ERROR


class EvaluationTaskStatus(IntEnum):
    WAITING = 1
    RUNNING = 2
    DONE = 3
    SUBMITTED = 4
    ERROR = 5


class EvaluationTask(object):
    def __init__(self, index_location, index_type, eval_format, ranking_function=None, ranking_params=None,
                 topics_filename=None, topics_path=None, assessments_filename=None, assessments_path=None,
                 valid_ids_filename=None, valid_ids_path=None,
                 base_url=None, api_key=None, run_id=None, status=EvaluationTaskStatus.WAITING,
                 topics_md5=None, assessments_md5=None, time=None, _id=None, results=None, stats=None):
        self.index_location = index_location
        self.index_type = index_type
        self.eval_format = eval_format
        self.ranking_function = ranking_function
        self.ranking_params = ranking_params
        self.topics_filename = topics_filename
        self.topics_path = topics_path
        self.topics_md5 = topics_md5 or (md5(topics_path) if topics_path else None)
        self.assessments_filename = assessments_filename
        self.assessments_path = assessments_path
        self.assessments_md5 = assessments_md5 or (md5(assessments_path) if assessments_path else None)
        self.valid_ids_filename = valid_ids_filename
        self.valid_ids_path = valid_ids_path
        self.base_url = base_url
        self.api_key = api_key
        self.run_id = run_id
        self.status = EvaluationTaskStatus(status)
        self.time = time
        if results: self.results = results
        if stats: self.stats = stats
        if _id: self._id = str(_id)

    def __repr__(self):
        return json.dumps(self.__dict__)


class EvaluationTaskManager(object):
    def __init__(self, db_location, db_name, eval_location):
        self.tasks = []
        self.running = None

        self.eval_location = eval_location
        self.results_dirname = os.path.join(eval_location, 'results')
        self.assessments_dirname = os.path.join(eval_location, 'assessments')
        self.spool_dirname = os.path.join(eval_location, 'spool')

        os.makedirs(self.results_dirname, exist_ok=True)
        os.makedirs(self.assessments_dirname, exist_ok=True)
        os.makedirs(self.spool_dirname, exist_ok=True)

        db_location_parts = db_location.split(':')

        if len(db_location_parts) > 1:
            db_location = db_location_parts[0]
            db_port = int(db_location_parts[1])
        else:
            db_port = 27017

        try:
            self.client = MongoClient(db_location, db_port)
        except ConnectionFailure as e:
            raise ArmyAntException("Could not connect to MongoDB instance on %s:%s" % (db_location, db_port))

        self.db = self.client[db_name]

        # self.db['evaluation_tasks'].create_index([
        # ('topics_md5', pymongo.ASCENDING),
        # ('assessments_md5', pymongo.ASCENDING),
        # ('index_location', pymongo.ASCENDING),
        # ('index_type', pymongo.ASCENDING)
        # ], unique=True)
        self.db['evaluation_tasks'].create_index('run_id', unique=True)

    def add_task(self, task):
        self.tasks.append(task)

    def del_task(self, task_id):
        result = self.db['evaluation_tasks'].delete_one({'_id': ObjectId(task_id)}).deleted_count > 0
        self.clean_spool()
        self.clean_results_and_assessments()
        return result

    def reset_task(self, task_id):
        if self.running:
            self.running.interrupt = True
            if type(self.running) != LivingLabsEvaluator:
                self.running.remove_output()

        shutil.rmtree(os.path.join(self.eval_location, 'results', task_id), ignore_errors=True)
        shutil.rmtree(os.path.join(self.eval_location, 'assessments', task_id), ignore_errors=True)

        return self.db['evaluation_tasks'].update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': 1}}).matched_count > 0

    def rename_task(self, task_id, run_id):
        task = self.db['evaluation_tasks'].find_one(ObjectId(task_id))
        if task['eval_format'] == 'll-api': return False
        return self.db['evaluation_tasks'].update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'run_id': run_id}}).matched_count > 0

    def get_tasks(self):
        tasks = []
        for task in self.db['evaluation_tasks'].find().sort('time'):
            tasks.append(EvaluationTask(**task))
        return tasks

    def get_waiting_task(self, task_id=None):
        query = {'status': 1}
        if task_id: query['_id'] = task_id

        task = self.db['evaluation_tasks'].find_one_and_update(
            query, {'$set': {'status': 2}},
            sort=[('time', pymongo.ASCENDING)])
        if task: return EvaluationTask(**task)

    def reset_running_tasks(self):
        logger.warning("Resetting running tasks to the WAITING status")
        self.db['evaluation_tasks'].update_many(
            {'status': 2},
            {'$set': {'status': 1}})
        if not type(self.running) is LivingLabsEvaluator and self.running:
            self.running.remove_output()

    def queue(self):
        duplicate_error = False
        run_id_error = False

        inserted_ids = []
        for task in self.tasks:
            run_id_error = task.run_id is None or task.run_id.strip() == ''
            if run_id_error: continue
            try:
                task.time = int(round(time.time() * 1000))
                result = self.db['evaluation_tasks'].insert_one(task.__dict__)
                inserted_ids.append(result.inserted_id)
            except DuplicateKeyError as e:
                duplicate_error = True

        if duplicate_error:
            raise ArmyAntException("The Run ID must be unique.")

        if run_id_error:
            raise ArmyAntException("Tasks without a Run ID are not accepted")

        return inserted_ids

    def save(self, task, results, stats=None):
        self.db['evaluation_tasks'].update_one(
            {'_id': ObjectId(task._id)},
            {'$set': {'status': EvaluationTaskStatus.DONE, 'results': results, 'stats': stats}})

    def set_status(self, task, status):
        self.db['evaluation_tasks'].update_one(
            {'_id': ObjectId(task._id)},
            {'$set': {'status': status}})

    @contextmanager
    def get_results_summary(self, headers, metrics, decimals, fmt):
        tasks = list(self.db['evaluation_tasks'].find({'results': {'$exists': 1}}))
        if len(tasks) < 1: return

        with tempfile.NamedTemporaryFile() as tmp_file:
            columns = headers[:] if headers else []
            if metrics: columns.extend(metrics)
            df = pd.DataFrame(columns=columns)

            for task in tasks:
                task = EvaluationTask(**task)
                if not hasattr(task, 'results'): continue
                for result in task.results.values():
                    values = [None] * len(headers)
                    if 'Run ID' in columns: values[columns.index('Run ID')] = task.run_id
                    if 'Type' in columns: values[columns.index('Type')] = task.index_type
                    if 'Parameters' in columns:
                        params_id = ranking_params_to_params_id(result['ranking_params'])
                        values[columns.index('Parameters')] = params_id_to_str(params_id)
                    if 'Location' in columns: values[columns.index('Location')] = task.index_location
                    values.extend([
                        result['metrics'][metric]
                        if metric in result['metrics'] and result['metrics'][metric] != '' else np.nan
                        for metric in metrics
                    ])
                    df = df.append(pd.DataFrame([values], columns=columns))

            df.set_axis(axis=0, labels=range(len(df)), inplace=True)

            float_format_str = "%%.%df" % decimals
            float_format = lambda v: (float_format_str % v) if type(v) in (np.float, np.float64, float) else str(v)

            if fmt == 'csv':
                tmp_file.write(df.to_csv(index=False, float_format=float_format_str).encode('utf-8'))
            elif fmt == 'tex':
                for metric in metrics:
                    if not metric in df: continue
                    max_idx = df[metric].idxmax()
                    df.loc[max_idx, metric] = '{\\bf %s}' % float_format(df[metric][max_idx])
                    df.loc[~df.index.isin([max_idx]), metric] = df.loc[~df.index.isin([max_idx]), metric].apply(
                        float_format)
                tmp_file.write(df.to_latex(index=False, escape=False).encode('utf-8'))
            elif fmt == 'html':
                for metric in metrics:
                    if not metric in df: continue
                    max_idx = df[metric].idxmax()
                    df.loc[max_idx, metric] = '<b>%s</b>' % float_format(df[metric][max_idx])
                    df.loc[~df.index.isin([max_idx]), metric] = df.loc[~df.index.isin([max_idx]), metric].apply(
                        float_format)
                tmp_file.write(df.to_html(
                    index=False,
                    escape=False,
                    border=0,
                    justify='left',
                    classes='table table-sm table-scroll table-striped').encode('utf-8'))

            yield tmp_file

    @contextmanager
    def get_results_archive(self, task_id):
        task = self.db['evaluation_tasks'].find_one({'_id': ObjectId(task_id)})
        if task is None: return

        task = EvaluationTask(**task)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = os.path.join(tmp_dir, task_id)

            shutil.copytree(os.path.join(self.eval_location, 'assessments', task_id),
                            os.path.join(out_dir, 'evaluation_details'))
            shutil.copytree(os.path.join(self.eval_location, 'results', task_id),
                            os.path.join(out_dir, 'search_results'))

            sorted_ranking_params = sorted(task.ranking_params.keys()) if task.ranking_params else []

            if hasattr(task, 'results'):
                with open(os.path.join(out_dir, "eval_metrics.csv"), 'w') as f:
                    writer = csv.writer(f)
                    writer.writerow(sorted_ranking_params + ['metric', 'value'])
                    for params_id, results in task.results.items():
                        for metric, value in results['metrics'].items():
                            params = OrderedDict(sorted(
                                params_id_to_ranking_params(params_id),
                                key=lambda d: d[0]))
                            writer.writerow(list(params.values()) + [metric, value])

            if hasattr(task, 'stats'):
                with open(os.path.join(out_dir, "eval_stats.csv"), 'w') as f:
                    writer = csv.writer(f)
                    writer.writerow(sorted_ranking_params + ['stat', 'value'])
                    for params_id, stats in task.stats.items():
                        for stat, value in stats.items():
                            if type(value) is not dict and type(value) is not list:
                                params = OrderedDict(sorted(
                                    params_id_to_ranking_params(params_id),
                                    key=lambda d: d[0]))
                                writer.writerow(list(params.values()) + [stat, value])

            archive_filename = os.path.join(tmp_dir, '%s.zip' % task_id)
            with zipfile.ZipFile(archive_filename, 'w') as zipf:
                zipdir(out_dir, zipf)

            yield archive_filename

    def get_results_json(self, task_id):
        task = self.db['evaluation_tasks'].find_one({'_id': ObjectId(task_id)})
        if task is None: return

        task = EvaluationTask(**task)

        if task.eval_format == 'll-api':
            url = urljoin(task.base_url, 'api/v2/participant/outcome')
            auth = HTTPBasicAuth(task.api_key, '')
            headers = {'Content-Type': 'application/json'}
            r = requests.get(url, headers=headers, auth=auth)
            return r.json()

        return {}

    def clean_spool(self):
        valid_spool_filenames = set([])
        for task in self.db['evaluation_tasks'].find():
            if task['eval_format'] in ('inex', 'inex-xer', 'trec'):
                valid_spool_filenames.add(os.path.basename(task['topics_path']))
                if 'assessments_path' in task and task['assessments_path']:
                    valid_spool_filenames.add(os.path.basename(task['assessments_path']))

        for filename in os.listdir(self.spool_dirname):
            path = os.path.join(self.spool_dirname, filename)
            if os.path.isfile(path) and not filename in valid_spool_filenames and (
                    filename.startswith('eval_assessments_') or filename.startswith('eval_topics_')):
                logger.warning("Removing unreferenced spool file '%s'" % path)
                os.remove(path)

    def clean_results_and_assessments(self):
        valid_output_dirnames = set([])
        for task in self.db['evaluation_tasks'].find():
            valid_output_dirnames.add(os.path.basename(str(task['_id'])))

        for filename in os.listdir(self.results_dirname):
            path = os.path.join(self.results_dirname, filename)
            # 24 is the MongoDB ObjectId default length
            if not filename in valid_output_dirnames and len(filename) == 24:
                logger.warning("Removing unreferenced result directory '%s'" % path)
                shutil.rmtree(path)

        for filename in os.listdir(self.assessments_dirname):
            path = os.path.join(self.assessments_dirname, filename)
            # 24 is the MongoDB ObjectId default length
            if not filename in valid_output_dirnames and len(filename) == 24:
                logger.warning("Removing unreferenced assessments directory '%s'" % path)
                shutil.rmtree(path)

    async def process(self, task_id=None):
        try:
            self.clean_spool()
            self.clean_results_and_assessments()
            while True:
                try:
                    task = self.get_waiting_task(task_id=task_id)
                    if task:
                        try:
                            logger.info("Running evaluation task %s" % task._id)
                            if task.eval_format == 'll-api':
                                e = Evaluator.factory(task, '%s::%s::%s' % (task.base_url, task.api_key, task.run_id))
                            else:
                                e = Evaluator.factory(task, self.eval_location)

                            self.running = e
                            status = await e.run()

                            if task.eval_format in ('inex', 'inex-xer', 'trec'):
                                self.save(task, e.results, e.stats)
                                self.running = None
                            elif task.eval_format == 'll-api':
                                self.set_status(task, status)
                        except ArmyAntException as e:
                            logger.error("Could not run evaluation task %s: %s" % (task._id, str(e)))

                    if task_id: break
                    await asyncio.sleep(5)
                except Exception as e:
                    if type(e) is asyncio.CancelledError: raise
                    logger.exception(e)
        except asyncio.CancelledError:
            self.reset_running_tasks()