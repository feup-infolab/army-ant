#!/usr/bin/env python
#
# java_index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging
import re
import signal

import jpype
import yaml
import yamlordereddictloader
from jpype import JPackage, isJVMStarted, startJVM

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
    JVM_ARGS = jvm_config.get('args')

    if JVM_ARGS and len(JVM_ARGS) > 0:
        args_message = 'the following arguments: %s' % JVM_ARGS
    else:
        args_message = 'default arguments'
        JVM_ARGS = None

    logger.info("Starting JVM with %s" % args_message)

    if not isJVMStarted():
        args = [
            jpype.getDefaultJVMPath(),
            '-Djava.class.path=%s' % CLASSPATH,
        ]

        if JVM_ARGS is not None:
            for other_arg in re.split(r'[ ]+', JVM_ARGS):
                args.append(other_arg)

        startJVM(*args, convertStrings=False, ignoreUnrecognized=True)

    signal.signal(signal.SIGINT, handler)

    armyant = JPackage('armyant')
    JDocument = armyant.structures.Document
    JTriple = armyant.structures.Triple
    JEntity = armyant.structures.Entity
