#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# army-ant.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import fire, logging, asyncio
from army_ant.exception import ArmyAntException
from army_ant.reader import Reader
from army_ant.database import Database
from army_ant.index import Index
from army_ant.server import run_app
from army_ant.extras import fetch_wikipedia_images

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)

class CommandLineInterface(object):
    def index(self, source_path, source_reader, index_location='localhost', index_type='gow', db_location='localhost', db_name='graph_of_entity', db_type='mongo', limit=None):
        try:
            reader = Reader.factory(source_path, source_reader, limit)

            loop = asyncio.get_event_loop()
            try:
                index = Index.factory(reader, index_location, index_type, loop)
                if db_location and db_name and db_type:
                    db = Database.factory(db_location, db_name, db_type, loop)
                    loop.run_until_complete(db.store(index.index()))
                else:
                    loop.run_until_complete(index.index())
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except ArmyAntException as e:
            logger.error(e)

    def search(self, query, offset=0, limit=10, index_location='localhost', index_type='gow', db_location='localhost', db_name='graph_of_entity', db_type='mongo'):
        try:
            loop = asyncio.get_event_loop()
            try:
                index = Index.open(index_location, index_type, loop)
                response = loop.run_until_complete(index.search(query, offset, limit))

                if db_location and db_name and db_type:
                    db = Database.factory(db_location, db_name, db_type, loop)
                    metadata = loop.run_until_complete(db.retrieve(response['results']))
                
                for (result, i) in zip(response['results'], range(offset, offset+limit)):
                    print("===> %3d %7.2f %s" % (i+1, result['score'], result['docID']))
                    doc_id = result['docID']
                    if doc_id in metadata:
                        for item in metadata[doc_id].items():
                            print("\t%10s: %s" % item)
                        print()
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except ArmyAntException as e:
            logger.error(e)

    def server(self):
        loop = asyncio.get_event_loop()
        run_app(loop)

    def fetch_wikipedia_images(self, db_name, db_location='localhost', db_type='mongo'):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(fetch_wikipedia_images(db_location, db_name, db_type, loop))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

if __name__ == '__main__':
    fire.Fire(CommandLineInterface)
