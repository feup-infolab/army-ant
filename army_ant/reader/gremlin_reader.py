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


class GremlinReader(Reader):
    pass
