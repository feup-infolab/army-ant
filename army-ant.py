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

            loop = asyncio.get_event_loop()
            try:
                index = Index.factory(reader, index_location, index_type, loop)
                loop.run_until_complete(index.index())
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except ArmyAntException as e:
            logger.error(e)

    def search(self, query, index_location='localhost', index_type='gow'):
        try:
            loop = asyncio.get_event_loop()
            try:
                index = Index.open(index_location, index_type, loop)
                results = loop.run_until_complete(index.search(query))
                for (result, i) in zip(results, range(len(results))):
                    print("===> %3d %7.2f %s" % (i+1, result['score'], result['docID']))
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except ArmyAntException as e:
            logger.error(e)

    def server(self):
        loop = asyncio.get_event_loop()
        try:
            run_app(loop)
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

if __name__ == '__main__':
    fire.Fire(CommandLineInterface)
