#!/usr/bin/env python
#
# result_set.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import configparser
import itertools
import json
import logging
import math
import os
import re
import signal
import sqlite3
from collections import Counter, OrderedDict, defaultdict
from enum import Enum
from statistics import mean, variance

import igraph
import jpype
import numpy as np
import pandas as pd
import psycopg2
import tensorflow as tf
import tensorflow_ranking as tfr
import yaml
from aiogremlin import Cluster
from aiohttp.client_exceptions import ClientConnectorError
from jpype import (JException, JBoolean, JClass, JDouble, JPackage,
                   JString, isJVMStarted, java, shutdownJVM, startJVM)
from sklearn.externals import joblib
from sklearn.preprocessing import MinMaxScaler

from army_ant.exception import ArmyAntException
from army_ant.reader import Document, Entity
from army_ant.setup import config_logger
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.util.text import analyze

logger = logging.getLogger(__name__)


class ResultSet(object):
    def __init__(self, results, num_docs, trace=None, trace_ascii=None):
        self.results = results
        self.num_docs = num_docs
        self.trace = trace
        self.trace_ascii = trace_ascii

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        self.iter = iter(self.results)
        return self.iter

    def __next__(self):
        return next(self.iter)

    # For compatibility with external implementations depending on dictionaries
    def __getitem__(self, key):
        if key == 'results':
            return self.results
        elif key == 'numDocs':
            return self.num_docs
        elif key == 'trace':
            return self.trace
        elif key == 'traceASCII':
            return self.trace_ascii
        else:
            raise KeyError

    def __contains__(self, key):
        return (key == 'results' and self.results or
                key == 'numDocs' and self.num_docs or
                key == 'trace' and self.trace or
                key == 'traceASCII' and self.trace_ascii)

    def __repr__(self):
        return "[ %s ]" % ', '.join([str(result) for result in self.results])
