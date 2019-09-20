import csv
import glob
import itertools
import logging
import os
import re
import shelve
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

import pandas as pd
import requests
import requests_cache
from bs4 import BeautifulSoup, SoupStrainer
from lxml import etree
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from requests.auth import HTTPBasicAuth
from SPARQLWrapper.SPARQLExceptions import EndPointNotFound

from army_ant.exception import ArmyAntException
from army_ant.setup import config_logger
from army_ant.util import get_first, html_to_text, inex
from army_ant.util.dbpedia import fetch_dbpedia_triples
from army_ant.util.text import AhoCorasickEntityExtractor
from army_ant.reader import Reader, Document, Entity

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
