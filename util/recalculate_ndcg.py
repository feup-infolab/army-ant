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
    if len(sys.argv) < 3:
        print("Usage: %s SEARCH_RESULTS_DIRECTORY INEX_QRELS [P=10]" % sys.argv[0])
        sys.exit(1)

    dirpath = sys.argv[1]
    qrelspath = sys.argv[2]
    p = 10 if len(sys.argv) <= 3 else int(sys.argv[3])

    ideal_rankings = {}
    with open(qrelspath, 'r') as f:
        for line in f:
            qid, _, doc_id, rel, _ = line.split(' ', 4)
            if not qid in ideal_rankings: ideal_rankings[qid] = []
            ideal_rankings[qid].append(int(rel) > 0)

        for qid in ideal_rankings.keys():
            ideal_rankings[qid] = sorted(ideal_rankings[qid], reverse=True)

    print('params_id\tndcg@%d' % p)

    for subdirname in sorted(os.listdir(dirpath)):
        subdirpath = os.path.join(dirpath, subdirname)

        ndcgs = []
        for filename in glob.glob(os.path.join(subdirpath, '*.csv')):
            df = pd.read_csv(filename)
            qid = os.path.splitext(os.path.basename(filename))[0]
            dcg_p = dcg(df.relevant, p)
            idcg_p = dcg(ideal_rankings[qid], p)
            ndcg = safe_div(dcg_p, idcg_p)
            ndcgs.append(ndcg)
        
        print('%s\t%.10f' % (subdirname, safe_div(sum(ndcgs), len(ndcgs))))
