#!/usr/bin/python
# -*- coding: utf8 -*-
#
# index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

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
    pass

class GraphOfEntity(Index):
    pass
