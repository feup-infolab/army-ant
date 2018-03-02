#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# stats
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-02

import numpy as np
import pandas as pd

from army_ant.exception import ArmyAntException
from army_ant.util import FillMethod, fill_missing


def gmean(values):
    return np.exp(np.mean(np.log(np.array(values) + 1e-20))) - 1e-20


def kendall_w(pd_dfs):
    pd_dfs = fill_missing(pd_dfs, 'doc_id', rank=FillMethod.INC_MAX, score=FillMethod.ZERO)

    rankings = np.stack([df.sort_values('doc_id')['rank'] for df in pd_dfs], axis=0)

    if rankings.ndim != 2:
        raise ArmyAntException('Rankings matrix must be 2-dimensional')

    m = rankings.shape[0] # rankers
    n = rankings.shape[1] # documents

    return (12 * m * np.var(np.sum(rankings, axis=0))) / (m ** 2 * (n ** 3 - n))


if __name__ == '__main__':
    df1 = pd.DataFrame([[1, 2, 3], [10, 4, 2], ['d1', 'd2', 'd3']], index=['rank', 'score', 'doc_id']).T
    df2 = pd.DataFrame([[1, 2, 3, 4], [20, 8, 4, 2], ['d1', 'd2', 'd7', 'd3']], index=['rank', 'score', 'doc_id']).T
    df3 = pd.DataFrame([[1, 2, 3], [100, 40, 20], ['d2', 'd1', 'd3']], index=['rank', 'score', 'doc_id']).T
    print(kendall_w([df1, df2, df3]))
