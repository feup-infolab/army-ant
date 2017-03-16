#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# army-ant.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import fire, logging, asyncio
from army_ant.exception import ArmyAntException
from army_ant.reader import Reader
from army_ant.index import Index
from army_ant.server import run_app

logging.basicConfig(
    format='army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

class CommandLineInterface(object):
    def index(self, source_path, source_reader, index_location='localhost', index_type='gow'):
        try:
            reader = Reader.factory(source_path, source_reader)
            index = Index.factory(reader, index_location, index_type)
            index.index()
        except ArmyAntException as e:
            logger.error(e)

    def search(self, query, index_location='localhost', index_type='gow'):
        try:
            index = Index.open(index_location, index_type)
            index.search(query, self.loop)
        except ArmyAntException as e:
            logger.error(e)

    def server(self):
        run_app(asyncio.get_event_loop())

if __name__ == '__main__':
    fire.Fire(CommandLineInterface)
