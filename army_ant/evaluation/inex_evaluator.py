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
from army_ant.evaluation import FilesystemEvaluator


logger = logging.getLogger(__name__)


class INEXEvaluator(FilesystemEvaluator):
    def __init__(self, task, eval_location, query_type, retrieval_task):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)
        self.query_type = query_type
        self.retrieval_task = retrieval_task

    def get_topic_assessments(self):
        topic_doc_judgements = {}

        if not os.path.exists(self.task.assessments_path):
            raise ArmyAntException("Topic assessments file not found: %s" % self.task.assessments_path)

        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                if self.retrieval_task == Index.RetrievalTask.entity_retrieval:
                    topic_id, _, id, _, judgement = line.split(' ', 4)
                    judgement = int(judgement)
                    if judgement == 2:
                        judgement = 0
                else:
                    topic_id, _, id, judgement, _ = line.split(' ', 4)
                    judgement = int(judgement)
                    if judgement > 0:
                        judgement = 1

                if not topic_id in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][id] = judgement

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
        if not os.path.exists(o_results_path):
            os.makedirs(o_results_path)

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
                if self.query_type == Index.QueryType.entity:
                    query = '||'.join(topic.xpath('entities/entity/text()'))
                else:
                    categories = topic.xpath('categories/category/text()')
                    query += ' %s' % ' '.join(categories)

            logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (
                query, topic_id, self.task.index_type, self.task.index_location))
            start_time = time.time()
            engine_response = await self.index.search(
                query, 0, 10000, task=self.retrieval_task,
                ranking_function=self.task.ranking_function, ranking_params=ranking_params)
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
