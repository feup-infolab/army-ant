import logging

from . import Index

logger = logging.getLogger(__name__)

class NullIndex(Index):
    async def index(self, features_location=None):
        count = 0

        for doc in self.reader:
            count += 1

            if count % 1000 == 0:
                logger.info("%d documents read" % count)

            yield doc

        logger.info("%d documents read" % count)
