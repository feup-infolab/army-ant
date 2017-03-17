#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# extras.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-17

import logging, pymongo, re, requests
from lxml import html
from army_ant.exception import ArmyAntException
from army_ant.database import Database

logger = logging.getLogger(__name__)

async def fetch_wikipedia_images(db_location, db_type, loop):
    db = Database.factory(db_location, db_type, loop)
    async for record in db.cursor():
        if 'metadata' in record and 'url' in record['metadata']:
            url = record['metadata']['url']
            match = re.match(r'http[s]?://[^.]+\.wikipedia\.org/wiki/(.*)', url)
            if not match:
                logger.warn("%s is not a Wikipedia URL, skipping" % url)
                next

            page = requests.get(url)
            tree = html.fromstring(page.content)
            img_url = tree.xpath('(//table[contains(@class, "infobox")]//img)[1]/@src')
            if len(img_url) > 0:
                await db.set_metadata(record['doc_id'], 'img_url', img_url[0])
