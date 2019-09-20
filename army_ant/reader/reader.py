#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

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

logger = logging.getLogger(__name__)


class Reader(object):
    @staticmethod
    def factory(source_path, source_reader, features_location=None, limit=None):
        import army_ant.reader as rd

        if source_reader == 'wikipedia_data':
            return rd.WikipediaDataReader(source_path)
        elif source_reader == 'inex':
            return rd.INEXReader(source_path, include_dbpedia=False, limit=limit)
        elif source_reader == 'inex_dbpedia':
            return rd.INEXReader(source_path, include_dbpedia=True, limit=limit)
        elif source_reader == 'inex_dir':
            return rd.INEXDirectoryReader(source_path, include_dbpedia=False, limit=limit)
        elif source_reader == 'inex_dir_dbpedia':
            return rd.INEXDirectoryReader(source_path, include_dbpedia=True, limit=limit)
        elif source_reader == 'living_labs':
            return rd.LivingLabsReader(source_path, limit)
        elif source_reader == 'wapo':
            return rd.TRECWashingtonPostReader(source_path, limit=limit)
        elif source_reader == 'wapo_doc_profile':
            return rd.TRECWashingtonPostReader(
                source_path, features_location=features_location, include_ae_doc_profile=True, limit=limit)
        elif source_reader == 'wapo_dbpedia':
            return rd.TRECWashingtonPostReader(source_path, include_dbpedia=True, limit=limit)
        elif source_reader == 'wapo_doc_profile_dbpedia':
            return rd.TRECWashingtonPostReader(
                source_path, features_location=features_location, include_ae_doc_profile=True, include_dbpedia=True,
                limit=limit)
        elif source_reader == 'csv':
            return rd.CSVReader(source_path)
        # elif source_reader == 'gremlin':
        #     return rd.GremlinReader(source_path)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def __iter__(self):
        return self

    def __next__(self):
        raise ArmyAntException("Reader __next__ not implemented")


class Document(object):
    def __init__(self, doc_id, title=None, text=None, links=None, entities=None, triples=None, metadata=None):
        self.doc_id = doc_id
        self.title = title
        self.text = text
        self.links = links
        self.entities = entities
        self.triples = triples
        self.metadata = metadata

    def __repr__(self):
        entities = [] if self.entities is None else [str(entity) for entity in self.entities]
        triples = [] if self.triples is None else [str(triple) for triple in self.triples]
        metadata = [] if self.metadata is None else [str((k, v)) for k, v in self.metadata.items()]

        return (
            '-----------------\n'
            'DOC ID:\n%s\n\n'
            'TITLE:\n%s\n\n'
            'TEXT (%d chars):\n%s\n%s\n\n'
            'ENTITIES (%d):\n%s\n'
            'TRIPLES (%d):\n%s\n%s\n\n'
            'METADATA:\n%s\n'
            '-----------------\n'
        ) % (
            self.doc_id,
            self.title,
            len(self.text), self.text[0:2000], '[...]' if len(self.text) > 2000 else '',
            len(entities), ', '.join(entities[0:5]),
            len(triples), '\n\n'.join(triples[0:5]),
            '[...]' if len(triples) > 5 else '', '\n'.join(metadata)
        )


class Entity(object):
    def __init__(self, label, uri=None):
        self.label = label
        self.uri = uri

    def __repr__(self):
        if self.uri: return "(%s, %s)" % (self.label, self.uri)
        return "%s" % self.label