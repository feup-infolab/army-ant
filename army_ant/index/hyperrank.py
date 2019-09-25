# !/usr/bin/env python

# hyperrank.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-03-15

import logging
from enum import Enum

from army_ant.index import Index, Result, ResultSet  # noqa
from army_ant.util.text import textrank  # noqa

logger = logging.getLogger(__name__)


# XXX There is already a HyperRank ranking function. This is for the R implementation. Which one should we rename?
# XXX Maybe we should implement an algebra solver using power iteration and numba instead of doing it in R.
# XXX The idea is to do this for a hypergraph matrix representation, but which representation?
class HyperRank(Index):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)
        self.index_features = [HyperRank.Feature[index_feature] for index_feature in index_features]

    async def index(self, features_location=None):
        if HyperRank.Feature.keywords in self.index_features:
            logger.info("Indexing top %.0f%% keywords per document based on TextRank" %
                        (HyperRank.KW_RATIO * 100))

        for doc in self.reader:
            yield doc

    async def search(self, query, offset, limit, query_type=None, task=None,
                     ranking_function=None, ranking_params=None, debug=False):
        return ResultSet()
