#!/usr/bin/env python
#
# recalculate_ndcg.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-07-18

import pandas as pd
import sys
import os
import glob
import math

def dcg(rel, p):
    return sum(rel[i-1] / math.log2(i + 1) for i in range(1, min(len(rel), p) + 1))

def safe_div(a, b):
    return 0 if b == 0 else a / b

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s SEARCH_RESULTS_DIRECTORY [P=10]" % sys.argv[0])
        sys.exit(1)

    dirpath = sys.argv[1]
    p = 10 if len(sys.argv) <= 2 else int(sys.argv[2])

    print('params_id\tndcg@%d' % p)

    for subdirname in sorted(os.listdir(dirpath)):
        subdirpath = os.path.join(dirpath, subdirname)

        ndcgs = []
        for filename in glob.glob(os.path.join(subdirpath, '*.csv')):
            df = pd.read_csv(filename)
            ideal_ranking = sorted(df.relevant, reverse=True)
            dcg_p = dcg(df.relevant, p)
            idcg_p = dcg(ideal_ranking, p)
            ndcg = safe_div(dcg_p, idcg_p)
            ndcgs.append(ndcg)
        
        print('%s\t%.10f' % (subdirname, safe_div(sum(ndcgs), len(ndcgs))))
