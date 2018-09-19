#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# analysis.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-02-28

import logging

import numpy as np
import pandas as pd
from lxml import etree

from army_ant.exception import ArmyAntException
from army_ant.index import Index
from army_ant.util import get_first, os
from army_ant.util.stats import gmean, kendall_w, spearman_rho

logger = logging.getLogger(__name__)


async def rws_rank_correlation(index_a_location, index_a_type, index_b_location, index_b_type,
                               ranking_fun_a, ranking_fun_b, ranking_params_a, ranking_params_b,
                               topics_path, output_path, cutoff, repeats, method, force, loop):
    assert method in ('spearman')

    index_a = Index.open(index_a_location, index_a_type, loop)
    index_b = Index.open(index_b_location, index_b_type, loop)
    topics = etree.parse(topics_path)

    os.makedirs(output_path, exist_ok=True)

    correlations = pd.DataFrame(columns=['l', 'r', 'topic_id'])

    for topic in topics.xpath('//topic'):
        topic_id = get_first(topic.xpath('@id'))
        query = get_first(topic.xpath('title/text()'))

        logger.info("Processing topic %s [ %s ]" % (topic_id, query))

        path = os.path.join(output_path, 'l_%d-r_%d' % (rw_length[i], rw_repeats[j]), 'topic_%s' % topic_id)
        os.makedirs(path, exist_ok=True)

        rhos = []
        num_results_a = []
        num_results_b = []

        for repeat in range(1, repeats + 1):
            filename_a = os.path.join(path, 'a_repeat_%%0%dd.csv' % len(str(repeats)) % repeat)
            filename_b = os.path.join(path, 'b_repeat_%%0%dd.csv' % len(str(repeats)) % repeat)

            if not force and os.path.exists(filename_a):
                df_a = pd.read_csv(filename_a)
                num_results_a.append(len(df_a))
                logger.warning("Loading existing file for repeat %d of index A: %s (use --force to recompute)" % (
                    repeat, filename_a))
                continue

            if not force and os.path.exists(filename_b):
                df_b = pd.read_csv(filename_b)
                num_results_b.append(len(df_b))
                logger.warning("Loading existing file for repeat %d of index B: %s (use --force to recompute)" % (
                    repeat, filename_b))
                continue

            result_set_a = await index_a.search(query, 0, cutoff, ranking_fun_a, ranking_params_a)
            df_a = pd.DataFrame(columns=['score', 'doc_id'])

            for result in result_set_a:
                df_a = df_a.append({
                    'score': result.score,
                    'doc_id': result.doc_id
                }, ignore_index=True)

            df_a.index += 1
            df_a.to_csv(filename_a, index_label='rank')

            logger.info("Saved repeat %d for index A in %s" % (repeat, filename_a))

            num_results_a.append(len(result_set_a))

            result_set_b = await index_b.search(query, 0, cutoff, ranking_fun_b, ranking_params_b)
            df_b = pd.DataFrame(columns=['score', 'doc_id'])

            for result in result_set_b:
                df_b = df_b.append({
                    'score': result.score,
                    'doc_id': result.doc_id
                }, ignore_index=True)

            df_b.index += 1
            df_b.to_csv(filename_b, index_label='rank')

            logger.info("Saved repeat %d for index B in %s" % (repeat, filename_b))

            num_results_b.append(len(result_set_b))

            rhos.append(spearman_rho(df_a, df_b))

        correlations = correlations.append({
            'l': rw_length[i],
            'r': rw_repeats[j],
            'topic_id': topic_id,
            'avg_num_results_a': np.mean(num_results_a),
            'avg_num_results_b': np.mean(num_results_b),
            'avg_rho': np.mean(rhos)
        }, ignore_index=True)

    correlations_filename = os.path.join(output_path, 'correlations_per_topic-%d_repeats.csv' % repeats)
    correlations.to_csv(correlations_filename, index=False)
    logger.info(
        "Saved correlations per topic (%d repeats) to %s" % (repeats, correlations_filename))

    gmean_correlations = correlations[['l', 'r', 'avg_rho']] \
        .groupby(['l', 'r']) \
        .agg(lambda x: gmean(x.values))

    gmean_correlations_filename = os.path.join(output_path, 'gmean_correlations-%d_repeats.csv' % repeats)
    gmean_correlations.to_csv(gmean_correlations_filename)
    logger.info("Saved geometric mean for correlations (%d repeats) to %s" % (repeats, gmean_correlations_filename))


async def rws_rank_concordance(index_location, index_type, rw_length, rw_repeats, topics_path, output_path,
                               cutoff, repeats, method, force, loop):
    assert method in ('kendall_w')

    index = Index.open(index_location, index_type, loop)
    topics = etree.parse(topics_path)

    os.makedirs(output_path, exist_ok=True)

    correlations = pd.DataFrame(columns=['l', 'r', 'topic_id'])

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

                    result_set = await index.search(query, 0, cutoff, 'random_walk',
                                                    {'l': str(rw_length[i]), 'r': str(rw_repeats[j])})
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

                correlations = correlations.append({
                    'l': rw_length[i],
                    'r': rw_repeats[j],
                    'topic_id': topic_id,
                    'avg_num_results': np.mean(num_results),
                    'w': kendall_w(df_repeats)
                }, ignore_index=True)

    correlations_filename = os.path.join(output_path, 'concordances_per_topic-%d_repeats.csv' % repeats)
    correlations.to_csv(correlations_filename, index=False)
    logger.info(
        "Saved concordances per topic (%d repeats) to %s" % (repeats, correlations_filename))

    gmean_correlations = correlations[['r', 'l', 'w']] \
        .groupby(['l', 'r']) \
        .agg(lambda x: gmean(x.values))

    gmean_correlations_filename = os.path.join(output_path, 'gmean_concordances-%d_repeats.csv' % repeats)
    gmean_correlations.to_csv(gmean_correlations_filename)
    logger.info("Saved geometric mean concordances (%d repeats) to %s" % (repeats, gmean_correlations_filename))
