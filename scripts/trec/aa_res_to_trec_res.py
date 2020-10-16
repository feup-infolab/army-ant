#!/usr/bin/env python
#
# aa_res_to_trec_res.py
# José Devezas <joseluisdevezas@gmail.com>
# 2020-10-16

import glob
import os
import sys

import pandas as pd

if len(sys.argv) < 2:
    print("%s RESULTS_DIR" % sys.argv[0])
    sys.exit(1)

run_id = os.path.basename(os.path.dirname(sys.argv[1]))

print("qid\titer\tdocno\trank\tsim\trun_id")

for filename in glob.glob(os.path.join(sys.argv[1], "*.csv")):
    qid = os.path.splitext(os.path.basename(filename))[0]
    res = pd.read_csv(filename)

    for _, row in res.iterrows():
        print("\t".join([qid, "Q0", str(row['doc_id']), str(row['rank']), str(row['score']), run_id]))
