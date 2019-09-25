#!/usr/bin/env python
#
# java_index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging
import signal

import jpype
import yaml
import yamlordereddictloader
from jpype import (JPackage, isJVMStarted, startJVM)

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

        startJVM(*args, convertStrings=True)

    signal.signal(signal.SIGINT, handler)

    armyant = JPackage('armyant')
    JDocument = armyant.structures.Document
    JTriple = armyant.structures.Triple
    JEntity = armyant.structures.Entity
