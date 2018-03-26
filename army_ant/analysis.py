#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# analysis.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-02-28

import logging

import pandas as pd
import numpy as np
from lxml import etree

from army_ant.index import Index
from army_ant.util import get_first, os
from army_ant.util.stats import kendall_w, gmean

logger = logging.getLogger(__name__)


async def random_walk_concordance_test(index_location, index_type, ranking_function, rw_length, rw_repeats,
                                       topics_path, output_path, limit, repeats, method, force, loop):
    assert method in ('kendall_w')

    index = Index.open(index_location, index_type, loop)
    topics = etree.parse(topics_path)

    os.makedirs(output_path, exist_ok=True)

    concordances = pd.DataFrame(columns=['l', 'r', 'topic_id'])

    for i in range(len(rw_length)):
        for j in range(len(rw_repeats)):
            for topic in topics.xpath('//topic'):
                topic_id = get_first(topic.xpath('@id'))
                query = get_first(topic.xpath('title/text()'))

                logger.info("Processing topic %s [ %s ], using l = %d and r = %d" % (
                    topic_id, query, rw_length[i], rw_repeats[j]))

                path = os.path.join(output_path, 'l_%d-r_%d' % (rw_length[i], rw_repeats[j]), 'topic_%s' % topic_id)
                os.makedirs(path, exist_ok=True)

                df_repeats = []
                num_results = []

                for repeat in range(1, repeats + 1):
                    filename = os.path.join(path, 'repeat_%%0%dd.csv' % len(str(repeats)) % repeat)

                    if not force and os.path.exists(filename):
                        df = pd.read_csv(filename)
                        df_repeats.append(df)
                        num_results.append(len(df))
                        logger.warning("Loading existing file for repeat %d: %s (use --force to recompute)" % (
                            repeat, filename))
                        continue

                    result_set = await index.search(query, 0, limit, ranking_function,
                                                    { 'l': str(rw_length[i]), 'r': str(rw_repeats[j]) })
                    df = pd.DataFrame(columns=['score', 'doc_id'])

                    for result in result_set:
                        df = df.append({
                            'score': result.score,
                            'doc_id': result.doc_id
                        }, ignore_index=True)

                    df.index += 1
                    df.to_csv(filename, index_label='rank')

                    logger.info("Saved repeat %d in %s" % (repeat, filename))

                    df_repeats.append(pd.read_csv(filename))
                    num_results.append(len(result_set))

                concordances = concordances.append({
                    'l': rw_length[i],
                    'r': rw_repeats[j],
                    'topic_id': topic_id,
                    'avg_num_results': np.mean(num_results),
                    'w': kendall_w(df_repeats)
                }, ignore_index=True)

    concordances_filename = os.path.join(output_path, 'concordances_per_topic-%d_repeats.csv' % repeats)
    concordances.to_csv(concordances_filename, index=False)
    logger.info(
        "Saved concordances per topic (%d repeats) to %s" % (repeats, concordances_filename))

    gmean_concordances = concordances[['r', 'l', 'w']] \
        .groupby(['l', 'r']) \
        .agg(lambda x: gmean(x.values))

    gmean_concordances_filename = os.path.join(output_path, 'gmean_concordances-%d_repeats.csv' % repeats)
    gmean_concordances.to_csv(gmean_concordances_filename)
    logger.info("Saved geometric mean concordances (%d repeats) to %s" % (repeats, gmean_concordances_filename))
