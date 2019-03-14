#!/usr/bin/env python
#
# service_index.py
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

from . import Index

logger = logging.getLogger(__name__)


class ServiceIndex(Index):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        index_location_parts = self.index_location.split('/')
        if len(index_location_parts) > 1:
            self.index_path = index_location_parts[1]
        else:
            self.index_path = None

        index_location_parts = index_location_parts[0].split(':')
        if len(index_location_parts) > 1:
            self.index_host = index_location_parts[0]
            self.index_port = index_location_parts[1]
        else:
            self.index_host = index_location_parts[0]
            self.index_port = 8182
