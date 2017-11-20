#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# database.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-17

import logging, pymongo
from pymongo import MongoClient
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Database(object):
    @staticmethod
    def factory(db_location, db_name, db_type, loop):
        if db_type == 'mongo':
            return MongoDatabase(db_location, db_name, loop)
        else:
            raise ArmyAntException("Unsupported database type %s" % db_type)

    def __init__(self, db_location, db_name, loop):
        self.db_location = db_location
        self.db_name = db_name
        self.loop = loop

    async def store(self, index):
        raise ArmyAntException("Store not implemented for %s" % self.__class__.__name__)

    async def retrieve(self, results):
        raise ArmyAntException("Retrieve not implemented for %s" % self.__class__.__name__)

class MongoDatabase(Database):
    def __init__(self, db_location, db_name, loop):
        super().__init__(db_location, db_name, loop)
        
        db_location_parts = db_location.split(':')
        
        if len(db_location_parts) > 1:
            db_location = db_location_parts[0]
            db_port = int(db_location_parts[1])
        else:
            db_port = 27017

        self.client = MongoClient(db_location, db_port)
        self.db = self.client[self.db_name]

    async def store(self, index):
        logger.info("Storing metadata for all documents")
        async for doc in index:
            logger.debug("Storing metadata for %s" % doc.doc_id)
            self.db['documents'].update_one(
                { 'doc_id': doc.doc_id },
                { '$set': {'doc_id': doc.doc_id, 'metadata': doc.metadata } },
                upsert=True)

    async def retrieve(self, results=None):
        logger.info("Retrieving metadata for matching documents")

        metadata = {}
        records = self.db['documents'].find({ 'doc_id': { '$in': [doc["docID"] for doc in results] } })

        for record in records:
            metadata[record['doc_id']] = record['metadata']

        return metadata

    async def cursor(self):
        logger.info("Iterating over metadata for all documents")
        for record in self.db['documents'].find():
            yield record

    async def set_metadata(self, doc_id, key, value):
        logger.info("Setting %s=%s for %s" % (key, value, doc_id))
        self.db['documents'].update_one(
            { 'doc_id': doc_id },
            { '$set': { 'metadata.%s' % key: value } })
