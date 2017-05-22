#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# evaluation.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-19

import json, time, pymongo, asyncio, logging, csv, os, shutil, tempfile, zipfile, math
from enum import IntEnum
from lxml import etree
from datetime import datetime
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from army_ant.index import Index
from army_ant.util import md5, get_first, zipdir
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Evaluator(object):
    @staticmethod
    def factory(task, eval_location):
        if task.eval_format == 'inex':
            return INEXEvaluator(task, eval_location)
        else:
            raise ArmyAntException("Unsupported evaluator format")

    def __init__(self, task, eval_location):
        self.task = task
        self.results = {}

        self.start_date = datetime.now()
        
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
        shutil.rmtree(self.o_results_path)
        shutil.rmtree(self.o_assessments_path)

    async def run(self):
        raise ArmyAntException("Unsupported evaluator format %s" % eval_format)

class INEXEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)

    def get_assessed_topic_ids(self):
        topic_ids = set([])
        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                topic_id, _ = line.split(' ', 1)
                topic_ids.add(topic_id)
        return topic_ids

    def get_topic_assessments(self):
        logger.info("Loading topic assessments")

        topic_doc_judgements = {}

        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                topic_id, _, doc_id, judgement, _ = line.split(' ', 4)
                if not topic_id in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][doc_id] = int(judgement)

        return topic_doc_judgements

    async def get_topic_results(self, filter=None):
        topic_doc_judgements = self.get_topic_assessments()

        topics = etree.parse(self.task.topics_path)
        
        for topic in topics.xpath('//topic'):
            topic_id = get_first(topic.xpath('@id'))

            if filter and not topic_id in filter:
                logger.warning("Skipping topic '%s'" % topic_id)
                continue
            
            query = get_first(topic.xpath('title/text()'))
            
            logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (query, topic_id, self.task.index_type, self.task.index_location))
            engine_response = await self.index.search(query, 0, 10000)

            with open(os.path.join(self.o_results_path, topic_id), 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['rank', 'doc_id', 'relevant'])
                for i, result in zip(range(1, len(engine_response['results'])+1), engine_response['results']):
                    doc_id = result['docID']
                    relevant = topic_doc_judgements[topic_id][doc_id] > 0 if doc_id in topic_doc_judgements[topic_id] else False
                    writer.writerow([i, doc_id, relevant])
    
    def calculate_mean_average_precision(self):
        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        o_eval_details_file = os.path.join(self.o_assessments_path, 'map_average_precision_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'avg_precision'])

            avg_precisions = []
            for result_file in result_files:
                topic_id = os.path.basename(result_file)

                precisions = []
                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in reader:
                        results.append(row['relevant'] == 'True')

                    for i in range(1, len(results)+1):
                        rel = results[0:i]
                        p = sum(rel) / len(rel)
                        precisions.append(p)

                    avg_precision = 0.0 if len(precisions) == 0 else sum(precisions) / len(precisions)
                    avg_precisions.append(avg_precision)
                    writer.writerow([topic_id, avg_precision])

            self.results['MAP'] = sum(avg_precisions) / len(avg_precisions)

    def calculate_normalized_discounted_cumulative_gain_at_p(self, p=10):
        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        ndcgs = []
        for result_file in result_files:
            topic_id = os.path.basename(result_file)

            dcg_parcels = []
            idcg_parcels = []
            with open(result_file, 'r') as rf:
                reader = csv.DictReader(rf)
                results = []
                for row in reader:
                    results.append(row['relevant'] == 'True')

                for i in range(1, min(len(results), p) + 1):
                    rel = results[i-1]
                    dcg_p = rel / math.log2(i + 1)
                    dcg_parcels.append(dcg_p)

                for i in range(1, len(results)+1):
                    rel = results[i-1]
                    idcg_p = (2**rel - 1) / math.log2(i + 1)
                    idcg_parcels.append(idcg_p)

                ndcg = 0.0 if len(dcg_parcels) == 0 else sum(dcg_parcels) / len(idcg_parcels)
                ndcgs.append(ndcg)

        self.results['NDCG@%d' % p] = 0.0 if len(ndcgs) == 0 else sum(ndcgs) / len(ndcgs)

    async def run(self):
        assessed_topic_ids = self.get_assessed_topic_ids()
        await self.get_topic_results(assessed_topic_ids)
        self.calculate_mean_average_precision()
        self.calculate_normalized_discounted_cumulative_gain_at_p()

class EvaluationTaskStatus(IntEnum):
    WAITING = 1
    RUNNING = 2
    DONE = 3

class EvaluationTask(object):
    def __init__(self, topics_filename, topics_path, assessments_filename, assessments_path, index_location, index_type, eval_format,
                 status=EvaluationTaskStatus.WAITING, topics_md5=None, assessments_md5=None, time=None, _id=None, results=None):
        self.topics_filename = topics_filename
        self.topics_path = topics_path
        self.topics_md5 = topics_md5 or md5(topics_path)
        self.assessments_filename = assessments_filename
        self.assessments_path = assessments_path
        self.assessments_md5 = assessments_md5 or md5(assessments_path)
        self.index_location = index_location
        self.index_type = index_type
        self.eval_format = eval_format
        self.status = EvaluationTaskStatus(status)
        self.time = time
        if results: self.results = results
        if _id: self._id = str(_id)

    def __repr__(self):
        return json.dumps(self.__dict__)

class EvaluationTaskManager(object):
    def __init__(self, db_location, eval_location):
        self.tasks = []
        self.running = None

        self.eval_location = eval_location
        self.results_dirname = os.path.join(eval_location, 'results')
        self.assessments_dirname = os.path.join(eval_location, 'assessments')
        self.spool_dirname = os.path.join(eval_location, 'spool')

        db_location_parts = db_location.split(':')
        
        if len(db_location_parts) > 1:
            db_location = db_location_parts[0]
            db_port = int(db_location_parts[1])
        else:
            db_port = 27017

        self.client = MongoClient(db_location, db_port)
        self.db = self.client['army_ant']

        self.db['evaluation_tasks'].create_index([
            ('topics_md5', pymongo.ASCENDING),
            ('assessments_md5', pymongo.ASCENDING),
            ('index_location', pymongo.ASCENDING),
            ('index_type', pymongo.ASCENDING)
        ], unique=True)

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        tasks = []
        for task in self.db['evaluation_tasks'].find().sort('time'):
            tasks.append(EvaluationTask(**task))
        return tasks

    def get_waiting_task(self):
        task = self.db['evaluation_tasks'].find_one_and_update(
            { 'status': 1 },
            { '$set': { 'status': 2 } },
            sort=[('time', pymongo.ASCENDING)])
        if task: return EvaluationTask(**task)

    def reset_running_tasks(self):
        logger.warning("Resetting running tasks to the WAITING status")
        self.db['evaluation_tasks'].update_many(
            { 'status': 2 },
            { '$set': { 'status': 1 } })
        if self.running: self.running.remove_output()

    def queue(self):
        duplicate_error = False

        for task in self.tasks:
            try:
                task.time = int(round(time.time() * 1000))
                self.db['evaluation_tasks'].insert_one(task.__dict__)
            except DuplicateKeyError as e:
                duplicate_error = True

        if duplicate_error:
            raise ArmyAntException("You can only launch one task per topics + assessments + engine.")

    def save_results(self, task, results):
        self.db['evaluation_tasks'].update_one(
            { '_id': ObjectId(task._id) },
            { '$set': { 'status': EvaluationTaskStatus.DONE, 'results': results } })

    @contextmanager
    def get_results_archive(self, task_id):
        task = self.db['evaluation_tasks'].find_one({ '_id': ObjectId(task_id) })
        if task is None: return

        task = EvaluationTask(**task)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = os.path.join(tmp_dir, task_id)
            shutil.copytree(os.path.join(self.eval_location, 'assessments', task_id), out_dir)
            with open(os.path.join(out_dir, "eval_metrics.csv"), 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['metrics', 'value'])
                for metric, value in task.results.items():
                    writer.writerow([metric, value])
            archive_filename = os.path.join(tmp_dir, '%s.zip' % task_id)
            with zipfile.ZipFile(archive_filename, 'w') as zipf:
                zipdir(out_dir, zipf)
            yield archive_filename

    def clean_spool(self):
        valid_spool_filenames = set([])
        for task in self.db['evaluation_tasks'].find():
            valid_spool_filenames.add(os.path.basename(task['topics_path']))
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
            if not filename in valid_output_dirnames and len(filename) == 24: # 24 is the MongoDB ObjectId default length
                logger.warning("Removing unreferenced result directory '%s'" % path)
                shutil.rmtree(path)

        for filename in os.listdir(self.assessments_dirname):
            path = os.path.join(self.assessments_dirname, filename)
            if not filename in valid_output_dirnames and len(filename) == 24: # 24 is the MongoDB ObjectId default length
                logger.warning("Removing unreferenced assessments directory '%s'" % path)
                shutil.rmtree(path)

    async def process(self):
        try:
            self.clean_spool()
            self.clean_results_and_assessments()
            while True:
                task = self.get_waiting_task()
                if task:
                    try:
                        logger.info("Running evaluation task %s" % task._id)
                        e = Evaluator.factory(task, self.eval_location)
                        self.running = e
                        await e.run()
                        self.save_results(task, e.results)
                        self.running = None
                    except ArmyAntException as e:
                        logger.error("Could not run evaluation task %s: %s" % (task._id, str(e)))
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.reset_running_tasks()
