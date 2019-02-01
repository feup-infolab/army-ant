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
import logging
import os
import shelve
import shutil
import sys
import tempfile

import networkx as nx

logging.basicConfig(
    format='%(asctime)s link_graph_from_dump: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

if len(sys.argv) < 4:
    print("Usage: %s INPUT_GRAPH_PATH OUTPUT_GRAPH_PATH CLICKSTREAM_TSV_GZ [OUT_KV_DB_PATH]" % sys.argv[0])
    sys.exit(1)

in_graph_path = sys.argv[1]
out_graph_path = sys.argv[2]
clickstream_path = sys.argv[3]
tempdir_path = None

if len(sys.argv) > 4:
    shelve_path = sys.argv[4]
else:
    tempdir_path = tempfile.mkdtemp(prefix='army_ant_', suffix='_wikipedia_clickstream')
    logging.info("Using temporary directory %s" % tempdir_path)
    shelve_path = os.path.join(tempdir_path, 'transitions.idx')

if os.path.isfile(shelve_path):
    logging.info("Using existing clickstream index at %s" % shelve_path)
    requires_indexing = False
else:
    requires_indexing = True

with shelve.open(shelve_path) as db, gzip.open(clickstream_path, 'rt') as cs:
    if requires_indexing:
        logging.info("Indexing clickstream")
        c = 0

        for line in cs:
            prev, curr, type, n = line.strip().split('\t')
            n = int(n)
            if type == 'link':
                if not prev in db:
                    db[prev] = {}
                entry = db[prev]
                entry[curr] = n
                db[prev] = entry

                c += 1
                if c % 100000 == 0:
                    logging.info("%d transitions indexed" % c)

        logging.info("%d transitions indexed" % c)

    logging.info("Loading graph from %s" % in_graph_path)
    if in_graph_path.endswith('.gml') or in_graph_path.endswith('.gml.gz'):
        g = nx.read_gml(in_graph_path)
    else:
        g = nx.read_graphml(in_graph_path)

    logging.info("Adding transitions attribute to existing edges")
    c = 0
    for source, target in g.edges():
        if not source in db or not target in db[source]:
            g[source][target]['transitions'] = 0
        else:
            g[source][target]['transitions'] = db[source][target]
        c += 1
        if c % 10000 == 0:
            logging.info("%d (%.2f%%) edges processed" % (c, c / g.number_of_edges() * 100))
    logging.info("%d (%.2f%%) edges processed" % (c, c / g.number_of_edges() * 100))

    logging.info("Saving to %s" % out_graph_path)
    if out_graph_path.endswith('.gml') or out_graph_path.endswith('.gml.gz'):
        nx.write_gml(g, out_graph_path)
    else:
        nx.write_graphml(g, out_graph_path)

if tempdir_path:
    logging.info("Removing temporary directory %s" % tempdir_path)
    shutil.rmtree(tempdir_path)

logging.info("Done")
