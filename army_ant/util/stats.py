#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# stats
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-02

import os

import numpy as np
import pandas as pd

from scipy.stats import spearmanr

from army_ant.exception import ArmyAntException
from army_ant.util import FillMethod, fill_missing


def gmean(values):
    return np.exp(np.mean(np.log(np.array(values) + 1e-20))) - 1e-20


def kendall_w(pd_dfs):
    pd_dfs = fill_missing(pd_dfs, 'id', rank=FillMethod.INC_MAX, score=FillMethod.ZERO)

    rankings = np.stack([df.sort_values('id')['rank'] for df in pd_dfs], axis=0)

    if rankings.ndim != 2:
        raise ArmyAntException('Rankings matrix must be 2-dimensional')

    m = rankings.shape[0]  # rankers
    n = rankings.shape[1]  # documents

    return (12 * n * np.var(np.sum(rankings, axis=0))) / (m ** 2 * (n ** 3 - n))


def spearman_rho(df_a, df_b):
    dfs = fill_missing([df_a, df_b], 'id', rank=FillMethod.INC_MAX, score=FillMethod.ZERO)
    return round(spearmanr(dfs[0].sort_values('id')['rank'], dfs[1].sort_values('id')['rank']).correlation, 15)


if __name__ == '__main__':
    dfs = [
        pd.DataFrame({'rank': [1, 2, 3], 'score': [10, 4, 2], 'id': ['d1', 'd2', 'd3']}),
        pd.DataFrame({'rank': [1, 2, 3, 4], 'score': [20, 8, 4, 2], 'id': ['d1', 'd2', 'd7', 'd3']}),
        pd.DataFrame({'rank': [1, 2, 3], 'score': [100, 40, 20], 'id': ['d2', 'd1', 'd3']}),
        pd.DataFrame(columns=['rank', 'score', 'id'])
    ]
    #filled_dfs = fill_missing(dfs, 'id', rank=FillMethod.INC_MAX, score=FillMethod.ZERO)
    #for df in filled_dfs: print(df)
    print("Kendall's W:", kendall_w(dfs))
    print("Spearman's Rho:", spearman_rho(dfs[1], dfs[2]))

    # dir_path = '/opt/army-ant/analysis/inex-52t-nl-hgoe-rw_stability/l_2-r_100/topic_2010003'
    # dfs = [pd.read_csv(os.path.join(dir_path, filename)) for filename in os.listdir(dir_path)]
    # print("Kendall's W:", kendall_w(dfs))
