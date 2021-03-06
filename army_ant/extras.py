#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# extras.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-17

import logging
import re

import requests
from gensim.models import Word2Vec
from lxml import html
from requests.exceptions import RequestException

from army_ant.database import Database

logger = logging.getLogger(__name__)


async def fetch_wikipedia_images(db_location, db_name, db_type, loop):
    db = Database.factory(db_location, db_name, db_type, loop)
    async for record in db.without_img_url():
        if 'metadata' in record and 'url' in record['metadata']:
            url = record['metadata']['url']
            match = re.match(r'http[s]?://[^.]+\.wikipedia\.org/(wiki/(.*)|\?curid=\d+)', url)
            if not match:
                logger.warning("%s is not a Wikipedia URL, skipping" % url)
                next

            try:
                page = requests.get(url)
                tree = html.fromstring(page.content)
                img_url = tree.xpath('(//table[contains(@class, "infobox")]//img)[1]/@src')
                if len(img_url) > 0:
                    await db.set_metadata(record['doc_id'], 'img_url', img_url[0])
            except RequestException:
                logger.warning("Could not obtain image from %s, skipping" % url)


def word2vec_knn(model_path, word, k):
    try:
        model = Word2Vec.load(model_path)
        print(word, k)
        return model.wv.most_similar(positive=[word], topn=k)
    except KeyError:
        return


def word2vec_sim(model_path, word1, word2):
    try:
        model = Word2Vec.load(model_path)
        return model.wv.similarity(word1, word2)
    except KeyError:
        return
