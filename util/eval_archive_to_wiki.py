#!/usr/bin/env python
#
# eval_archive_to_wiki.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-09-19

import sys
import logging
import pandas as pd
from zipfile import ZipFile

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

decimal_places = 4
favorite_metrics = ['GMAP', 'MAP', 'NDCG@10', 'P@10']

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
    param_names = []

with ZipFile(sys.argv[1]) as f_zip:
    eval_metrics = [zip_obj for zip_obj in f_zip.filelist if zip_obj.filename.endswith('eval_metrics.csv')]
    if len(eval_metrics) < 1:
        logging.error("No eval_metrics.csv file found")
        sys.exit(2)

    if len(eval_metrics) > 1:
        logging.warning("Multiple eval_metrics.csv files found, using %s" % eval_metrics[0].filename)

    with f_zip.open(eval_metrics[0].filename, 'r') as f:
        df = pd.read_csv(f)

        df['Version'] = df[param_names].apply(lambda d: "%s(%s)" % (
            function_name,
            ', '.join(['%s=%s' % (p, x) for p, x in zip(param_names, d)])
        ) , axis=1)
        df = df[['Version', 'metric', 'value']].pivot(index='Version', columns='metric', values='value')
        df = df.reset_index().rename_axis(None, axis=1)[['Version'] + favorite_metrics]

        print('^ %s ^' % ' ^ '.join(df.columns.values) + ' Avg./Doc ^ Total ^ Avg./Query ^ Total ^')
        for row in df.iterrows():
            values = ['%%.%df' % decimal_places % d if type(d) is float else d for d in row[1:][0].values]
            print('| %s |' % ' | '.join(values) + (' ::: |' * 2) + (' |' * 2))