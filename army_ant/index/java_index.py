#!/usr/bin/env python
#
# java_index.py
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
import yamlordereddictloader
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

from . import Index

logger = logging.getLogger(__name__)


def handler(signum, frame): raise KeyboardInterrupt


class JavaIndex(Index):
    BLOCK_SIZE = 5000
    VERSION = '0.4-SNAPSHOT'
    CLASSPATH = 'external/java-impl/target/java-impl-%s-jar-with-dependencies.jar' % VERSION
    INSTANCES = {}

    config = yaml.load(open('config.yaml'), Loader=yamlordereddictloader.Loader)
    jvm_config = config['defaults'].get('jvm', {})
    MEMORY_MB = int(jvm_config.get('memory', '5120'))
    OTHER_ARGS = jvm_config.get('other_args')

    if OTHER_ARGS and len(OTHER_ARGS) > 0:
        args_message = 'the following additional arguments: %s' % OTHER_ARGS
    else:
        args_message = 'no additional arguments'
        OTHER_ARGS = None

    logger.info("Starting JVM with %s MB of heap and %s" % (MEMORY_MB, args_message))

    if not isJVMStarted():
        args = [
            jpype.getDefaultJVMPath(),
            '-Djava.class.path=%s' % CLASSPATH,
            '-Xms%dm' % MEMORY_MB,
            '-Xmx%dm' % MEMORY_MB
        ]

        if OTHER_ARGS is not None:
            args.append(OTHER_ARGS)

        startJVM(*args, convertStrings = True)

    signal.signal(signal.SIGINT, handler)

    armyant = JPackage('armyant')
    JDocument = armyant.structures.Document
    JTriple = armyant.structures.Triple
    JEntity = armyant.structures.Entity
