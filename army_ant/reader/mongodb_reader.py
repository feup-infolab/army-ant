import logging
import re

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from army_ant.exception import ArmyAntException
from army_ant.reader import Reader

logger = logging.getLogger(__name__)


class MongoDBReader(Reader):
    def __init__(self, source_path):
        super(MongoDBReader, self).__init__(source_path)

        db_location_parts = re.split(r'[:/]', source_path)

        if len(db_location_parts) >= 3:
            db_host = db_location_parts[0]
            db_port = int(db_location_parts[1])
            db_name = db_location_parts[1]
        elif len(db_location_parts) == 2:
            db_host = db_location_parts[0]
            db_port = 27017
            db_name = db_location_parts[1]
        else:
            db_host = 'localhost'
            db_port = 27017
            db_name = db_location_parts[0]

        try:
            self.client = MongoClient(db_host, db_port)
        except ConnectionFailure:
            raise ArmyAntException("Could not connect to MongoDB instance on %s:%s" % (db_host, db_port))

        self.db = self.client[db_name]
