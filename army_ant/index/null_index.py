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
            if os.path.exists(path):
                with open(path) as fp:
                    resume = int(fp.read())
                    logger.info("Skipping to document %d to resume collection processing" % resume)

        for doc in self.reader:
            count += 1

            if count % 1000 == 0:
                unprocessed_msg = " (ignored)" if count < resume else ""
                logger.info("%d documents read%s" % (count, unprocessed_msg))

            if resume is not None and count < resume:
                continue

            yield doc

        logger.info("%d documents read" % count)
