#!/usr/bin/env python
#
# graph_of_entity.py
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

from . import GremlinServerIndex

logger = logging.getLogger(__name__)


class GraphOfEntity(GremlinServerIndex):
    async def index(self, features_location=None):
        self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        self.client = await self.cluster.connect()

        for doc in self.reader:
            logger.info("Indexing %s" % doc.doc_id)
            logger.debug(doc.text)

            # Load entities and relations (knowledge base)
            for (e1, rel, e2) in doc.triples:
                logger.debug("%s -[%s]-> %s" % (e1.label, rel, e2.label))
                source_vertex = await self.get_or_create_vertex(e1.label, data={'doc_id': doc.doc_id, 'url': e1.url,
                                                                                'type': 'entity'})
                target_vertex = await self.get_or_create_vertex(e2.label, data={'url': e2.url, 'type': 'entity'})
                await self.get_or_create_edge(source_vertex, target_vertex, edge_type=rel)
                yield Document(doc_id=doc.doc_id, metadata={'url': e1.url, 'name': e1.label})
                # yield Document(doc_id = e2.url, metadata = { 'url': e2.url, 'name': e2.label }) # We're only
                # indexing what has a doc_id

            tokens = GraphOfEntity.analyze(doc.text)

            for i in range(len(tokens) - 1):
                # Load words, linking by sequential co-occurrence
                logger.debug("%s -[before]-> %s" % (tokens[i], tokens[i + 1]))
                source_vertex = await self.get_or_create_vertex(tokens[i], data={'type': 'term'})
                target_vertex = await self.get_or_create_vertex(tokens[i + 1], data={'type': 'term'})
                await self.get_or_create_edge(source_vertex, target_vertex, data={'doc_id': doc.doc_id})

            doc_entity_labels = set([])
            for e1, _, e2 in doc.triples:
                doc_entity_labels.add(e1.label.lower())
                doc_entity_labels.add(e2.label.lower())

            # Order does not matter / a second loop over unique tokens and entities should help
            for token in set(tokens):
                # Load word synonyms, linking to original term

                # syns = set([ss.name().split('.')[0].replace('_', ' ') for ss in wn.synsets(token)])
                # syns = syns.difference(token)

                # for syn in syns:
                # logger.debug("%s -[synonym]-> %s" % (token, syn))
                # syn_vertex = await self.get_or_create_vertex(syn, data={'type': 'term'})
                # edge = await self.get_or_create_edge(source_vertex, syn_vertex, edge_type='synonym')

                # Load word-entity occurrence

                source_vertex = await self.get_or_create_vertex(token, data={'type': 'term'})

                for entity_label in doc_entity_labels:
                    if re.search(r'\b%s\b' % re.escape(token), entity_label):
                        logger.debug("%s -[contained_in]-> %s" % (token, entity_label))
                        entity_vertex = await self.get_or_create_vertex(entity_label, data={'type': 'entity'})
                        await self.get_or_create_edge(source_vertex, entity_vertex, edge_type='contained_in')

                        # yield doc

        await self.cluster.close()

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        try:
            self.cluster = await Cluster.open(self.loop, hosts=[self.index_host], port=self.index_port)
        except ClientConnectorError:
            raise ArmyAntException("Could not connect to Gremlin Server on %s:%s" % (self.index_host, self.index_port))

        self.client = await self.cluster.connect()

        query_tokens = GraphOfEntity.analyze(query)

        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('graph_of_entity_query'), {
                'queryTokens': query_tokens,
                'offset': offset,
                'limit': limit
            })
        results = await result_set.one()
        await self.cluster.close()

        return results
