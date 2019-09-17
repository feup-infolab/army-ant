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
from army_ant.evaluation import Evaluator, LivingLabsEvaluator


logger = logging.getLogger(__name__)


class EvaluationTaskStatus(IntEnum):
    WAITING = 1
    RUNNING = 2
    DONE = 3
    SUBMITTED = 4
    ERROR = 5


class EvaluationTask(object):
    def __init__(self, index_location, index_type, eval_format, query_type=None, ranking_function=None,
                 ranking_params=None, topics_filename=None, topics_path=None,
                 assessments_filename=None, assessments_path=None, valid_ids_filename=None, valid_ids_path=None,
                 base_url=None, api_key=None, run_id=None, status=EvaluationTaskStatus.WAITING,
                 topics_md5=None, assessments_md5=None, time=None, _id=None, results=None, stats=None):
        self.index_location = index_location
        self.index_type = index_type
        self.eval_format = eval_format
        self.query_type = query_type
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
                if 'Parameters' in df:
                    df.Parameters = df.Parameters.apply(
                        lambda param_str: '<br>'.join(s for s in param_str[1:-1].split(', '))
                        if param_str != 'No parameters' else param_str)
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
            if task['eval_format'] in ('inex', 'inex-xer', 'inex-xer-elc', 'trec'):
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

                            if task.eval_format in ('inex', 'inex-xer', 'inex-xer-elc', 'trec'):
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
