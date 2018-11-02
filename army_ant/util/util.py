#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# util.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import hashlib
import os
from enum import Enum

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup


def html_to_text(html):
    soup = BeautifulSoup(html, "html5lib")

    for script in soup(["script", "style"]):
        script.extract()

    text = ''.join(soup.strings)

    lines = [line.strip() for line in text.splitlines()]
    chunks = [phrase.strip() for line in lines for phrase in line.split(' ')]
    text = ' '.join(chunk for chunk in chunks if chunk)

    return text


def load_gremlin_script(script_name):
    with open(os.path.join('gremlin', script_name + '.groovy'), 'r') as f:
        return f.read()


def load_sql_script(script_name):
    with open(os.path.join('sql', script_name + '.sql'), 'r') as f:
        return f.read()


def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


def get_first(lst, default=None):
    return next(iter(lst or []), default)


def zipdir(path, ziph):
    pwd = os.getcwd()
    os.chdir(os.path.dirname(path))
    for root, dirs, files in os.walk(os.path.basename(path)):
        for file in files:
            ziph.write(os.path.join(root, file))
    os.chdir(pwd)


def set_dict_defaults(d, defaults):
    for k, v in defaults.items():
        if isinstance(v, dict):
            set_dict_defaults(d.setdefault(k, {}), v)
        else:
            d.setdefault(k, v)


def safe_div(n, d):
    if d == 0: return 0
    return n / d


def typed_value(v):
    if v == 'True': return True
    if v == 'False': return False

    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def ranking_params_to_params_id(ranking_params):
    if ranking_params is None or len(ranking_params) < 1: return 'no_params'
    return '-'.join([p[0] + '_' + str(p[1]).replace('.', '~') for p in ranking_params.items()])


def params_id_to_str(params_id):
    if params_id == 'no_params': return "No parameters"
    params = []
    for p in params_id.split('-'):
        params.append(('%s=%s' % tuple(p.split('_', 1))).replace('~', '.'))
    return '(%s)' % ', '.join(params)


def params_id_to_ranking_params(s):
    if s == 'no_params': return []
    ranking_params = []
    for p in s.split('-'):
        parts = p.replace('~', '.').split('_', 1)
        parts[1] = typed_value(parts[1])
        ranking_params.append(tuple(parts))
    return ranking_params


# This is actually useless, as Python Fire already supports parsing for comma-separated values.
def interval_str_to_int_values(s):
    """
    Converts a string in the format '1-5,10-100:10,1000,1000' to a list ordered numbers:
    [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000].

    a-b will be converted to all numbers between a and b, including a and b and incrementing by 1.
    a-b:n will be converted to all numbers between a and b, including a and b and incrementing by n.
    All values are separated by a comma and single values are included as-is.

    If repeated values are generated, they are included only once.
    """

    int_values = []
    intervals = s.split(',')
    for interval in intervals:
        parts = interval.split('-')
        if len(parts) == 1:
            int_values.append(int(parts[0]))
        else:
            start = int(parts[0])
            end_by = parts[1].split(':')
            end = int(end_by[0])
            if len(end_by) == 1:
                int_values.extend(list(range(start, end + 1)))
            else:
                by = int(end_by[1])
                int_values.extend(list(range(start, end + 1, by)))
    return sorted(set(int_values))


class FillMethod(Enum):
    ZERO = 0
    INC_MAX = 1


def fill_missing(pd_dfs, key, **kwargs):
    result = []
    all_keys = set([])

    for df in pd_dfs:
        all_keys = all_keys.union(df[key])

    for df in pd_dfs:
        missing_keys = sorted(all_keys.difference(df[key]))
        missing_df = pd.DataFrame({key: missing_keys})

        for k, v in kwargs.items():
            if v == FillMethod.ZERO:
                missing_df[k] = 0
            elif v == FillMethod.INC_MAX:
                df_inc_max = df[k].max() + 1
                if np.isnan(df_inc_max): df_inc_max = 0 + 1
                missing_df[k] = range(df_inc_max, df_inc_max + len(missing_keys))

        df = df.append(missing_df)
        result.append(df)

    return result
