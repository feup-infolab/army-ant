#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# evaluation.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-19

import json, time, pymongo, asyncio, logging, configparser, csv, os
from enum import IntEnum
from lxml import etree
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from army_ant.index import Index
from army_ant.util import md5, get_first
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class INEXEvaluator(object):
    def __init__(self, topics_path, assessments_path, engine, eval_location):
        self.topics_path = topics_path
        self.assessments_path = assessments_path
        self.engine = engine
        self.o_results_path = os.path.join(eval_location, 'results')
        self.o_assessments_path = os.path.join(eval_location, 'assessments')

        config = configparser.ConfigParser()
        config.read('server.cfg')

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(
            config[engine].get('index_location'),
            config[engine].get('index_type'),
            self.loop)

    def get_assessed_topic_ids(self):
        topic_ids = set([])
        with open(self.assessments_path, 'r') as f:
            for line in f:
                topic_id, _ = line.split(' ', 1)
                topic_ids.add(topic_id)
        return topic_ids

    def get_topic_assessments(self):
        logger.info("Loading topic assessments")

        topic_doc_judgements = {}

        with open(self.assessments_path, 'r') as f:
            for line in f:
                topic_id, _, doc_id, judgement, _ = line.split(' ', 4)
                if not topic_id in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][doc_id] = int(judgement)

        return topic_doc_judgements

    async def get_topic_results(self, filter=None):
        topic_doc_judgements = self.get_topic_assessments()

        topics = etree.parse(self.topics_path)
        
        for topic in topics.xpath('//topic'):
            topic_id = get_first(topic.xpath('@id'))

            if filter and not topic_id in filter:
                logger.warning("Skipping topic '%s'" % topic_id)
                continue
            
            query = get_first(topic.xpath('title/text()'))
            
            logger.info("Obtaining results for query '%s' of topic '%s' using '%s' engine" % (query, topic_id, self.engine))
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

        avg_precisions = []
        for result_file in result_files:
            precisions = []
            with open(result_file, 'r') as f:
                reader = csv.DictReader(f)
                results = []
                for row in reader:
                    results.append(row['relevant'] == 'True')

                for i in range(1, len(results)+1):
                    rel = results[0:1]
                    p = sum(rel) / len(rel)
                    precisions.append(p)

                avg_precision = 0.0 if len(precisions) == 0 else sum(precisions) / len(precisions)
                avg_precisions.append(avg_precision)
        print("MAP:", sum(avg_precisions)/len(avg_precisions))

        
    async def run(self):
        #assessed_topic_ids = self.get_assessed_topic_ids()
        #await self.get_topic_results(assessed_topic_ids)
        self.calculate_mean_average_precision()

class EvaluationTaskStatus(IntEnum):
    WAITING = 1
    RUNNING = 2
    DONE = 3

class EvaluationTask(object):
    def __init__(self, topics_filename, topics_path, topics_format,
                 assessments_filename, assessments_path, assessments_format,
                 engine, status=EvaluationTaskStatus.WAITING,
                 topics_md5=None, assessments_md5=None, time=None, _id=None):
        self.topics_filename = topics_filename
        self.topics_path = topics_path
        self.topics_format = topics_format
        self.topics_md5 = topics_md5 or md5(topics_path)
        self.assessments_filename = assessments_filename
        self.assessments_path = assessments_path
        self.assessments_format = assessments_format
        self.assessments_md5 = assessments_md5 or md5(assessments_path)
        self.engine = engine
        self.status = EvaluationTaskStatus(status)
        self.time = time
        if _id: self._id = str(_id)

    def __repr__(self):
        return json.dumps(self.__dict__)

class EvaluationTaskManager(object):
    def __init__(self, db_location):
        self.tasks = []

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
            ('engine', pymongo.ASCENDING)
        ], unique=True)

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        tasks = []
        for task in self.db['evaluation_tasks'].find().sort('time'):
            tasks.append(EvaluationTask(**task))
        return tasks

    def get_waiting_task(self):
        return self.db['evaluation_tasks'].find_one_and_update(
            { 'status': 1 },
            { '$set': { 'status': 2 } },
            sort=[('time', pymongo.ASCENDING)])

    def reset_running_tasks(self):
        logger.warning("Resetting running tasks to the WAITING status")
        self.db['evaluation_tasks'].update_many(
            { 'status': 2 },
            { '$set': { 'status': 1 } })

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

    async def process(self):
        try:
            while True:
                print(self.get_waiting_task())
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.reset_running_tasks()
