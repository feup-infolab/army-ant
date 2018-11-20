#!/usr/bin/env python
#
# add_clickstream_transitions.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-11-20
#
# Using the publicly available clickstream data for October 2018, we store the number of transitions between
# linked pages in the Wikipedia link graph (e.g., a GraphML collected using rw_sample_link_graph.py)
# https://dumps.wikimedia.org/other/clickstream/2018-10/clickstream-enwiki-2018-10.tsv.gz
#

import gzip
import os
import shelve
import shutil
import sys
import tempfile

import networkx as nx

if len(sys.argv) < 4:
    print("Usage: %s INPUT_GRAPHML_GZ OUTPUT_GRAPHML_GZ CLICKSTREAM_TSV_GZ [OUT_KV_DB_PATH]" % sys.argv[0])
    sys.exit(1)

in_graphml_path = sys.argv[1]
out_graphml_path = sys.argv[2]
clickstream_path = sys.argv[3]
tempdir_path = None

if len(sys.argv) > 4:
    shelve_path = sys.argv[4]
else:
    tempdir_path = tempfile.mkdtemp(prefix='army_ant_', suffix='_wikipedia_clickstream')
    print("==> Using temporary directory %s" % tempdir_path)
    shelve_path = os.path.join(tempdir_path, 'transitions.idx')

if os.path.isfile(shelve_path):
    print("==> Using existing clickstream index at %s" % shelve_path)
    requires_indexing = False
else:
    requires_indexing = True

with shelve.open(shelve_path) as db, gzip.open(clickstream_path, 'rt') as cs:
    if requires_indexing:
        print("==> Indexing clickstream")
        c = 0

        for line in cs:
            prev, curr, type, n = line.strip().split('\t')
            n = int(n)
            if type == 'link':
                if not prev in db:
                    db[prev] = {}
                db[prev][curr] = n
                
                c += 1
                if c % 100000 == 0:
                    print("    %d transitions indexed" % c)            

        print("    %d transitions indexed" % c)

    print("==> Loading GraphML")
    g = nx.read_graphml(in_graphml_path)

    print("==> Adding transitions attribute to existing edges")
    for source, target in g.edges():
        if not source in db or not target in db[source]:
            print(source, target)
            g[source][target]['transitions'] = 0
        else:
            g[source][target]['transitions'] = db[source][target]

    print("==> Saving to %s" % out_graphml_path)
    nx.write_graphml(g, out_graphml_path)

if tempdir_path:
    print("==> Removing temporary directory %s" % tempdir_path)
    shutil.rmtree(tempdir_path)

print("==> Done")
