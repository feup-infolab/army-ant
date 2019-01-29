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
from army_ant.util.stats import gmean, kendall_w, spearman_rho, jaccard_index

logger = logging.getLogger(__name__)


async def rank_correlation(index_a_location, index_a_type, index_b_location, index_b_type,
                           ranking_fun_a, ranking_fun_b, ranking_params_a, ranking_params_b,
                           topics_path, output_path, cutoff, repeats, method, force, loop):
    assert method in ('spearman')

    index_a = Index.open(index_a_location, index_a_type, loop)
    index_b = Index.open(index_b_location, index_b_type, loop)
    topics = etree.parse(topics_path)

    os.makedirs(output_path, exist_ok=True)

    correlations = pd.DataFrame(columns=[
        'topic_id', 'index_type_a', 'ranking_funtion_a', 'ranking_params_a', 'avg_num_results_a',
        'index_type_b', 'ranking_funtion_b', 'ranking_params_b', 'avg_num_results_b', 'avg_rho'])

    for topic in topics.xpath('//topic'):
        topic_id = get_first(topic.xpath('@id'))
        query = get_first(topic.xpath('title/text()'))

        logger.info("Processing topic %s [ %s ]" % (topic_id, query))

        path = os.path.join(output_path, 'topic_%s' % topic_id)
        os.makedirs(path, exist_ok=True)

        rhos = []
        jaccards = []
        num_results_a = []
        num_results_b = []

        for repeat in range(1, repeats + 1):
            filename_a = os.path.join(path, 'a_repeat_%%0%dd.csv' % len(str(repeats)) % repeat)
            filename_b = os.path.join(path, 'b_repeat_%%0%dd.csv' % len(str(repeats)) % repeat)

            if not force and os.path.exists(filename_a):
                df_a = pd.read_csv(filename_a, converters = { 'id': lambda d: str(d) })
                logger.warning("Loaded existing file for repeat %d of index A: %s (use --force to recompute)" % (
                    repeat, filename_a))
            else:
                result_set_a = await index_a.search(
                    query, 0, cutoff, task=Index.RetrievalTask.document_retrieval,
                    ranking_function=ranking_fun_a, ranking_params=ranking_params_a)
                df_a = pd.DataFrame(columns=['score', 'id'])

                for result in result_set_a:
                    df_a = df_a.append({
                        'score': result.score,
                        'id': result.id
                    }, ignore_index=True)

                df_a.index += 1
                df_a['rank'] = df_a.index
                df_a = df_a[['rank', 'score', 'id']]
                df_a.to_csv(filename_a, index=False)

                logger.info("Saved repeat %d for index A in %s" % (repeat, filename_a))

            if not force and os.path.exists(filename_b):
                df_b = pd.read_csv(filename_b, converters = { 'id': lambda d: str(d) })
                logger.warning("Loaded existing file for repeat %d of index B: %s (use --force to recompute)" % (
                    repeat, filename_b))
            else:
                result_set_b = await index_b.search(
                    query, 0, cutoff, task=Index.RetrievalTask.document_retrieval,
                    ranking_function=ranking_fun_b, ranking_params=ranking_params_b)
                df_b = pd.DataFrame(columns=['score', 'id'])

                for result in result_set_b:
                    df_b = df_b.append({
                        'score': result.score,
                        'id': result.id
                    }, ignore_index=True)

                df_b.index += 1
                df_b['rank'] = df_b.index
                df_b = df_b[['rank', 'score', 'id']]
                df_b.to_csv(filename_b, index=False)

                logger.info("Saved repeat %d for index B in %s" % (repeat, filename_b))

            num_results_a.append(len(df_a))
            num_results_b.append(len(df_b))
            rhos.append(spearman_rho(df_a, df_b))
            jaccards.append(jaccard_index(df_a, df_b))

        correlations = correlations.append({
            'topic_id': topic_id,
            'index_type_a': index_a_type,
            'ranking_funtion_a': ranking_fun_a,
            'ranking_params_a': '_'.join('_'.join(d) for d in ranking_params_a.items()),
            'avg_num_results_a': np.mean(num_results_a),
            'index_type_b': index_b_type,
            'ranking_funtion_b': ranking_fun_b,
            'ranking_params_b': '_'.join('_'.join(d) for d in ranking_params_b.items()),
            'avg_num_results_b': np.mean(num_results_b),
            'avg_rho': np.mean(rhos),
            'avg_jaccard': np.mean(jaccards)
        }, ignore_index=True)

    correlations_filename = os.path.join(output_path, 'comparison_per_topic-%d_repeats.csv' % repeats)
    correlations.to_csv(correlations_filename, index=False)
    logger.info(
        "Saved correlations per topic (%d repeats) to %s" % (repeats, correlations_filename))

    mean_correlation = np.mean(correlations['avg_rho'])
    mean_correlation_filename = os.path.join(output_path, 'mean_correlation-%d_repeats' % repeats)
    open(mean_correlation_filename, 'w').write('%15f' % mean_correlation)
    logger.info("Saved mean correlation (%d repeats) to %s" % (repeats, mean_correlation_filename))

    mean_jaccard = np.mean(correlations['avg_jaccard'])
    mean_jaccard_filename = os.path.join(output_path, 'mean_jaccard-%d_repeats' % repeats)
    open(mean_jaccard_filename, 'w').write('%15f' % mean_jaccard)
    logger.info("Saved mean Jaccard index (%d repeats) to %s" % (repeats, mean_jaccard_filename))


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
                        logger.warning("Loaded existing file for repeat %d: %s (use --force to recompute)" % (
                            repeat, filename))
                        continue

                    result_set = await index.search(query, 0, cutoff, 'random_walk',
                                                    {'l': str(rw_length[i]), 'r': str(rw_repeats[j])})
                    df = pd.DataFrame(columns=['score', 'id'])

                    for result in result_set:
                        df = df.append({
                            'score': result.score,
                            'id': result.id
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

    mean_correlation = correlations[['r', 'l', 'w']] \
        .groupby(['l', 'r']) \
        .agg(lambda x: gmean(x.values))

    mean_correlation_filename = os.path.join(output_path, 'gmean_concordances-%d_repeats.csv' % repeats)
    mean_correlation.to_csv(mean_correlation_filename)
    logger.info("Saved geometric mean concordances (%d repeats) to %s" % (repeats, mean_correlation_filename))
