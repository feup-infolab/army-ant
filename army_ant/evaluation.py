#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# evaluation.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-19

import json, time, pymongo
from enum import IntEnum
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from army_ant.util import md5
from army_ant.exception import ArmyAntException

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
        self._id = None if _id is None else str(_id)
        self._id = None

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
        for task in self.db['evaluation_tasks'].find():
            tasks.append(EvaluationTask(**task))
        return { 'tasks': tasks }

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
