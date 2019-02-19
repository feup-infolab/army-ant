#!/usr/bin/env python
#
# eval_archive_to_wiki.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-09-19

import datetime
import logging
import math
import numbers
import sys
from zipfile import ZipFile

import pandas as pd

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

decimal_places = 4
favorite_metrics = ['GMAP', 'MAP', 'NDCG@10', 'P@10']

def millis_format(millis):
    if not isinstance(millis, numbers.Number) or math.isnan(millis):
        return "N/A"

    out = {}
    out['days'] = millis // 86400000
    millis -= out['days'] * 86400000
    out['hours'] = millis // 3600000
    millis -= out['hours'] * 3600000
    out['minutes'] = millis // 60000
    millis -= out['minutes'] * 60000
    out['seconds'] = millis // 1000
    millis -= out['seconds'] * 1000
    out['millis'] = millis
    if out['days'] == 0:
        del out['days']
        if out['hours'] == 0:
            del out['hours']
            if out['minutes'] == 0:
                del out['minutes']
                if out['seconds'] == 0:
                    del out['seconds']
    return '%s%s%s%s%s' % (
        '%.2dd ' % out['days'] if 'days' in out else '',
        '%.2dh ' % out['hours'] if 'hours' in out else '',
        '%.2dm ' % out['minutes'] if 'minutes' in out else '',
        '%.2ds ' % out['seconds'] if 'seconds' in out else '',
        '%.3dms' % out['millis'])

if len(sys.argv) < 2:
    print("Usage: %s ARCHIVE [FUNCTION_NAME] [PARAM_NAMES ...]" % sys.argv[0])
    sys.exit(1)

if len(sys.argv) > 2:
    function_name = sys.argv[2]
else:
    function_name = 'score'

if len(sys.argv) > 3:
    param_names = sys.argv[3:]
else:
    param_names = None

with ZipFile(sys.argv[1]) as f_zip:
    eval_metrics = [zip_obj for zip_obj in f_zip.filelist if zip_obj.filename.endswith('eval_metrics.csv')]

    if len(eval_metrics) < 1:
        logging.error("No eval_metrics.csv file found")
        sys.exit(2)

    if len(eval_metrics) > 1:
        logging.warning("Multiple eval_metrics.csv files found, using %s" % eval_metrics[0].filename)

    eval_stats = [zip_obj for zip_obj in f_zip.filelist if zip_obj.filename.endswith('eval_stats.csv')]

    if len(eval_stats) < 1:
        logging.error("No eval_stats.csv file found")
        sys.exit(2)

    if len(eval_stats) > 1:
        logging.warning("Multiple eval_stats.csv files found, using %s" % eval_stats[0].filename)

    with f_zip.open(eval_metrics[0].filename, 'r') as f:
        df = pd.read_csv(f)

        if param_names is None:
            param_names = [col for col in df.columns if not col in ['metric', 'value']]

        df['Version'] = df[param_names].apply(lambda d: "%s(%s)" % (
            function_name,
            ', '.join(['%s=%s' % (p, x) for p, x in zip(param_names, d)])
        ) , axis=1)
        df = df[['Version', 'metric', 'value']].pivot(index='Version', columns='metric', values='value')
        eval_metrics_df = df.reset_index().rename_axis(None, axis=1)[['Version'] + favorite_metrics]

    with f_zip.open(eval_stats[0].filename, 'r') as f:
        df = pd.read_csv(f)
        print(df)

        df['Version'] = df[param_names].apply(lambda d: "%s(%s)" % (
            function_name,
            ', '.join(['%s=%s' % (p, x) for p, x in zip(param_names, d)])
        ) , axis=1)
        df['value'] = df['value'].apply(millis_format)
        df = df[['Version', 'stat', 'value']].pivot(index='Version', columns='stat', values='value')
        eval_stats_df = df.reset_index().rename_axis(None, axis=1)\
            .rename(columns={'avg_query_time': 'Avg./Query', 'total_query_time': 'Total Query Time' })

    df = pd.merge(eval_metrics_df, eval_stats_df, how='outer', on='Version')
    df['Avg./Doc'] = pd.Series(['N/A'] + [':::'] * (len(df.index)-1))
    df['Total Indexing Time'] = pd.Series(['N/A'] + [':::'] * (len(df.index)-1))

    df = df[['Version'] + favorite_metrics + ['Avg./Doc', 'Total Indexing Time', 'Avg./Query', 'Total Query Time']]

    print('^ %s ^' % ' ^ '.join(df.columns.values))
    for row in df.iterrows():
        values = ['%%.%df' % decimal_places % d if type(d) is float else d for d in row[1:][0].values]
        print('| %s |' % ' | '.join(values))
