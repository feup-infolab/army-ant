#!/usr/bin/env python
#
# hyperrank.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-03-15

import logging

from army_ant.index import Index, Result, ResultSet

logger = logging.getLogger(__name__)


class HyperRank(Index):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)

    async def index(self, features_location=None):
        for doc in self.reader:
            yield doc

    async def search(self, query, offset, limit, task=None, ranking_function=None, ranking_params=None, debug=False):
        return ResultSet()
