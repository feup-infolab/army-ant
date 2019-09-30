import csv
import logging
import os
from enum import Enum

from army_ant.util.text import textrank

from . import Index

logger = logging.getLogger(__name__)


class TextIndex(Index):
    class Feature(Enum):
        keywords = 'EXTRACT_KEYWORDS'

    def __init__(self, reader, index_location, index_features, loop):
        super().__init__(reader, index_location, loop)

        self.index_features = [TextIndex.Feature[index_feature] for index_feature in index_features]
        self.index_filename = os.path.join(self.index_location, "index.csv")

        os.makedirs(self.index_location, exist_ok=True)

    async def index(self, features_location=None):
        if TextIndex.Feature.keywords in self.index_features:
            logger.info("Indexing top %.0f%% keywords per document based on TextRank" % (Index.KW_RATIO * 100))

        resume = None
        if features_location:
            path = os.path.join(features_location, "resume")
            if os.path.exists(path):
                with open(path) as fp:
                    resume = int(fp.read())
                    logger.info("Skipping to document %d to resume collection processing" % resume)

        count = 0

        with open(self.index_filename, 'w') as fp:
            csv_writer = csv.writer(fp, delimiter='\t')

            if TextIndex.Feature.keywords in self.index_features:
                csv_writer.writerow(['doc_id', 'keywords'])
            else:
                csv_writer.writerow(['doc_id', 'text'])

            for doc in self.reader:
                count += 1

                if count % 1000 == 0:
                    logger.info("%d documents read" % count)

                if not doc.doc_id:
                    logger.warning("Document %d does not have a 'doc_id', skipping" % count)
                    continue

                if TextIndex.Feature.keywords in self.index_features:
                    doc.text = '||'.join(textrank(doc.text, ratio=Index.KW_RATIO, as_list=True))

                if not doc.text:
                    logger.warning("Document %d (%s) does not have a text block, skipping" % (count, doc.doc_id))
                    continue

                csv_writer.writerow([doc.doc_id, doc.text])

                yield doc

        logger.info("%d documents read" % count)
