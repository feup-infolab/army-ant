#!/usr/bin/python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

from army_ant.exception import ArmyAntException

class Reader(object):
    @staticmethod
    def factory(source_path, source_reader):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def __iter__(self):
        raise ArmyAntException("Reader not implemented")

    def next(self):
        raise ArmyAntException("Reader not implemented")

class WikipediaDataReader(Reader):
    def __init__(self, source_path):
        super(WikipediaDataReader, self).__init__(source_path)
