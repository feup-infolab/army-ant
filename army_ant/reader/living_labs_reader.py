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


class LivingLabsReader(Reader):
    def __init__(self, source_path, limit=None):
        super(LivingLabsReader, self).__init__(source_path)
        self.limit = limit

        base_url, api_key = source_path.split('::')

        self.base_url = urljoin(base_url, "/api/v2/participant/")
        self.api_key = api_key
        self.headers = {'Content-Type': 'application/json'}
        self.auth = HTTPBasicAuth(api_key, '')

        requests_cache.install_cache('living_labs_cache', expire_after=10800)

        self.docs = self.get_docs()
        self.idx = 0

        if self.limit:
            self.docs = self.docs[0:self.limit]

    def get_docs(self):
        logging.info("Retrieving Living Labs documents")
        r = requests.get(urljoin(self.base_url, 'docs'), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        return r.json()['docs']

    def format_author_name(self, name):
        if name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                return '%s %s' % (parts[1].strip(), parts[0].strip())
        return name

    def to_text(self, doc, fields=['title'], content_fields=['abstract']):
        text = [doc[field] for field in fields]
        text.extend([doc['content'][field] for field in content_fields])
        return '\n'.join(filter(lambda d: d is not None, text))

    def to_triples(self, doc,
                   content_fields=['author', 'language', 'issued', 'publisher', 'type', 'subject', 'description']):
        triples = []
        for field in content_fields:
            if field in doc['content'] and doc['content'][field]:
                if field == 'author':
                    doc['content'][field] = self.format_author_name(doc['content'][field])
                triples.append((Entity(doc['docid']), Entity(field), Entity(doc['content'][field])))
        return triples

    def __next__(self):
        if self.idx >= len(self.docs):
            raise StopIteration
        else:
            doc = self.docs[self.idx]
            self.idx += 1
            return Document(
                doc_id=doc['docid'],
                text=self.to_text(doc),
                triples=self.to_triples(doc))
