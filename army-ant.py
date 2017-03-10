#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# army-ant.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import fire, logging
from army_ant.exception import ArmyAntException
from army_ant.reader import Reader
from army_ant.index import Index

logging.basicConfig(
    format='army-ant: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().setLevel(logging.DEBUG)

class CommandLineInterface(object):
    def index(self, source_path, source_reader, index_path, index_type='gow'):
        try:
            reader = Reader.factory(source_path, source_reader)
            index = Index.factory(reader, index_path, index_type)
            index.index()

        except ArmyAntException as e:
            logging.error(e)

if __name__ == '__main__':
    fire.Fire(CommandLineInterface)
