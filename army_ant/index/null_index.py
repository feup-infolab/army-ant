import logging
import os

from . import Index

logger = logging.getLogger(__name__)


class NullIndex(Index):
    async def index(self, features_location=None):
        count = 0

        resume = None
        if features_location:
            path = os.path.join(features_location, "resume")
            print(path)
            if os.path.exists(path):
                print(path)
                with open(path) as fp:
                    resume = int(fp.read())
                    logger.info("Resuming from %d" % resume)

        for doc in self.reader:
            count += 1
            if resume is not None and count < resume:
                continue

            if count % 1000 == 0:
                logger.info("%d documents read" % count)

            yield doc

        logger.info("%d documents read" % count)
