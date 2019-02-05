#!/usr/bin/env python
#
# wapo_link_graph_from_mongo.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-02-05

import logging
import sys
import warnings

import networkx as nx
from bs4 import BeautifulSoup
from pymongo import MongoClient


logging.basicConfig(
    format='%(asctime)s link_graph_from_dump: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')


if len(sys.argv) < 3:
    print("Usage: %s MONGO_DBNAME OUTPUT_GRAPH_PATH" % sys.argv[0])
    sys.exit(1)


database = sys.argv[1]
output_graph_path = sys.argv[2]


graph = {}

mongo = MongoClient()
db = mongo[database]


def document_iterator():
    for doc in db.articles.find():
        yield doc
    for doc in db.blog_posts.find():
        yield doc


logging.info("Extracting anchors from content elements (using article_url as node ID)")

edge_count = 0

for doc in document_iterator():
    if not 'contents' in doc or doc.get('contents') is None:
        continue

    source = doc['article_url']

    if not source in graph:
        graph[source] = set([])

    for par in doc['contents']:
        if par is None:
            continue

        html = par.get('content')
        if html is None:
            continue
        html = str(html)

        soup = BeautifulSoup(html, 'lxml')

        anchors = soup.find_all('a')

        for a in anchors:
            target = a.attrs.get('href')
            if target is None:
                continue

            graph[source].add(target)

            edge_count += 1
            if edge_count % 100000 == 0:
                logging.info("%d edges read (with duplicates)" % edge_count)

logging.info("%d edges read (with duplicates)" % edge_count)


logging.info("Converting into networkx format as a DiGraph")
g = nx.DiGraph()
g.add_edges_from((k, v) for k, vs in graph.items() for v in vs)


logging.info("Saving graph to %s" % output_graph_path)
if output_graph_path.endswith('.gml') or output_graph_path.endswith('.gml.gz'):
    nx.write_gml(g, output_graph_path)
else:
    nx.write_graphml(g, output_graph_path)
