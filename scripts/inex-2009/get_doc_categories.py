#!/usr/bin/env python
#
# get_doc_categories.py
# José Devezas <joseluisdevezas@gmail.com>
# 2020-04-28

import csv
import glob
import logging
import os
import sys
import tarfile

from lxml import etree


def get_first(lst, default=None):
    return next(iter(lst or []), default)


def xlink_to_page_id(xlink):
    _, filename = os.path.split(xlink)
    return os.path.splitext(filename)[0]


logging.basicConfig(
    format='%(asctime)s army-ant: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

if len(sys.argv) < 3:
    print("Usage: %s INEX_CORPUS_DIR OUTPUT_CSV" % sys.argv[0])
    sys.exit(1)

logger = logging.getLogger(__name__)

file_paths = glob.glob(os.path.join(sys.argv[1], '*.tar.bz2'))
csv_path = sys.argv[2]

parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)

with open(csv_path, 'w') as csv_f:
    csv_w = csv.writer(csv_f)

    num_docs = 0
    for file_path in file_paths:
        logger.info("Reading %s archive" % file_path)

        with tarfile.open(file_path, 'r|bz2') as tar:
            csv_w.writerow(['id', 'title', 'categories'])

            for member in tar:
                if not member.name.endswith('.xml'):
                    continue

                num_docs += 1

                if num_docs % 5000 == 0:
                    logger.info("%d documents processed so far" % num_docs)

                try:
                    article = etree.parse(tar.extractfile(member), parser)
                    page_id = xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                    title = get_first(article.xpath('//header/title/text()'))
                    categories = article.xpath('//header/categories/category/text()')

                    csv_w.writerow([page_id, title, ','.join(categories)])
                except etree.XMLSyntaxError:
                    logger.warning(
                        "Error parsing XML, skipping title indexing for %s in %s" % (member.name, file_path))

        logger.info("%d documents processed so far" % num_docs)

    logger.info("Valid categories per document saved in %s" % csv_path)
