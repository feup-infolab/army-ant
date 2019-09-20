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


class CSVReader(Reader):
    def __init__(self, source_path, doc_id_suffix=':doc_id', text_suffix=':text'):
        super(CSVReader, self).__init__(source_path)

        self.reader = csv.DictReader(open(source_path, newline=''))
        self.doc_id_suffix = doc_id_suffix
        self.text_suffix = text_suffix

        if not any([fieldname.endswith(self.text_suffix) for fieldname in self.reader.fieldnames]):
            raise ArmyAntException(
                "CSV must have at least one column name with a %s suffix (other supported suffixes include %s)" % (
                    self.text_suffix, self.doc_id_suffix))

    def __next__(self):
        for row in self.reader:
            doc_id = None
            text = []

            for k in row.keys():
                if k.endswith(self.text_suffix):
                    text.append(row[k])
                elif k.endswith(self.doc_id_suffix):
                    doc_id = row[k]

            text = '\n'.join(text)

            return Document(doc_id=doc_id, text=text)

        raise StopIteration
