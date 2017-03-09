#!/usr/bin/python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import string
from nltk import word_tokenize
from nltk.corpus import stopwords
from bulbs.neo4jserver import Graph, Config, NEO4J_URI
from army_ant.exception import ArmyAntException

class Index(object):
    @staticmethod
    def factory(reader, index_path, index_type):
        if index_type == 'gow':
            return GraphOfWord(reader, index_path)
        elif index_type == 'goe':
            return GraphOfEntity(reader, index_path)
        else:
            raise ArmyAntException("Unsupported index type %s" % index_type)

    def __init__(self, reader, index_path):
        self.reader = reader
        self.index_path = index_path

    def index(self):
        raise ArmyAntException("Graph index not implemented")

class GraphOfWord(Index):
    def __init__(self, index_path, index_type):
        super(GraphOfWord, self).__init__(index_path, index_type)
        config = Config(NEO4J_URI, "neo4j", "password")
        self.g = Graph(config)

    def index(self):
        for doc in self.reader:
            tokens = word_tokenize(doc.text.lower())
            tokens = [token for token in tokens if token not in stopwords.words('english') and not token[0] in string.punctuation]

            for i in range(len(tokens)-1):
                source_vertex = self.g.vertices.index.lookup(token=tokens[i])
                if not source_vertex:
                    source_vertex = self.g.vertices.create(token=tokens[i])

                target_vertex = self.g.vertices.index.lookup(token=tokens[i+1])
                if not target_vertex:
                    target_vertex = self.g.vertices.create(token=tokens[i+1])

                edge = g.edges.create(source_vertex, 'before', target_vertex)
                edge.doc_id = doc.doc_id
                edge.save()


class GraphOfEntity(Index):
    pass
