#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# analysis.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-02-28

from lxml import etree

from army_ant.index import Index
from army_ant.util import get_first


async def random_walk_concordance_test(index_location, index_type, rw_length, rw_repeats, topics_path, output_path,
                                       repeats, method, loop):
    assert method in ('kendall_w')

    index = Index.open(index_location, index_type, loop)
    topics = etree.parse(topics_path)

    for i in range(len(rw_length)):
        for j in range(len(rw_repeats)):
            print(rw_length[i], rw_repeats[j])
            for topic in topics.xpath('//topic'):
                topic_id = get_first(topic.xpath('@id'))
                query = get_first(topic.xpath('title/text()'))
                print(topic_id, query)
                print(await index.search(query, 0, 10))
