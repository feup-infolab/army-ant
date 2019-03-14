#!/usr/bin/env python
#
# result.py
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
from jpype import (JavaException, JBoolean, JClass, JDouble, JPackage, JString,
                   isJVMStarted, java, shutdownJVM, startJVM)
from sklearn.externals import joblib
from sklearn.preprocessing import MinMaxScaler

from army_ant.exception import ArmyAntException
from army_ant.reader import Document, Entity
from army_ant.setup import config_logger
from army_ant.util import load_gremlin_script, load_sql_script
from army_ant.util.text import analyze

logger = logging.getLogger(__name__)


class Result(object):
    def __init__(self, score, id, name, type=None, components=None):
        self.id = id
        self.name = name
        self.type = type
        self.score = score
        self.components = components

    def set_component(self, key, value):
        if self.components is None:
            self.components = []
        self.components[key] = value

    def unset_component(self, key):
        del self.components[key]
        if len(self.components) == 0:
            self.components = None

    def __getitem__(self, key):
        if key == 'id':
            return self.id
        elif key == 'name':
            return self.name
        elif key == 'type':
            return self.type
        elif key == 'score':
            return self.score
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return (key == 'id' and self.id or
                key == 'name' and self.name or
                key == 'type' and self.type or
                key == 'score' and self.score)

    def __repr__(self):
        return """{ "score": %f, "id": %s, "name": %s, "type": %s, "has_components": %s }""" % (
            self.score, self.id, self.name, self.type, ("true" if self.components else "false"))
