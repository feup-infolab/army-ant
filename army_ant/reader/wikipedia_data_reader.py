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


class WikipediaDataReader(Reader):
    def __init__(self, source_path):
        super().__init__(source_path)
        tar = tarfile.open(source_path)
        self.f = tar.extractfile(tar.getmember('wikipedia_datav1.0/wikipedia.train'))

    def to_plain_text(self, html):
        return html_to_text(html)

    def to_wikipedia_entity(self, label):
        return Entity(label, "http://en.wikipedia.org/wiki/%s" % label.replace(" ", "_"))

    def to_triples(self, entity, html):
        soup = BeautifulSoup(html, 'html.parser', parse_only=SoupStrainer('a'))

        triples = []
        for link in soup:
            if link.has_attr('relation'):
                triples.append((
                    self.to_wikipedia_entity(entity),
                    Entity(link['relation']),
                    self.to_wikipedia_entity(link['title'])))

        return triples

    def __next__(self):
        url = None
        entity = None
        html = ''
        for line in self.f:
            line = line.decode('utf-8')
            if line == '\n':
                return Document(
                    doc_id=url,
                    title=entity,
                    text=self.to_plain_text(html),
                    triples=self.to_triples(entity, html),
                    metadata={'url': url, 'name': entity})

            elif line.startswith('url='):
                match = re.search(r'url=(http://[^.]+\.wikipedia\.org/wiki/(.*))', line.strip())
                if match:
                    url = match.group(1)
                    entity = match.group(2).replace('_', ' ')

            else:
                html = html + line

        raise StopIteration
