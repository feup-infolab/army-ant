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
    format='%(asctime)s wapo_link_graph_from_mongo: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')


if len(sys.argv) < 3:
    print("Usage: %s MONGO_DBNAME OUTPUT_GRAPH_PATH" % sys.argv[0])
    sys.exit(1)


database = sys.argv[1]
output_graph_path = sys.argv[2]


mongo = MongoClient()
db = mongo[database]


def document_iterator():
    for doc in db.articles.find():
        yield doc
    for doc in db.blog_posts.find():
        yield doc


logging.info("Extracting anchors from content elements (using article_url as node ID) and building graph")

g = nx.DiGraph()

doc_count = 0
edge_count = 0

attr_keys = ['id', 'title', 'article_url', 'published_date', 'author', 'type']

for source in document_iterator():
    if not 'contents' in source or source.get('contents') is None:
        continue

    for par in source['contents']:
        if par is None:
            continue

        html = par.get('content')
        if html is None:
            continue
        html = str(html)

        soup = BeautifulSoup(html, 'lxml')

        anchors = soup.find_all('a')

        for a in anchors:
            target_url = a.attrs.get('href')
            if target_url is None:
                continue

            query = {'article_url': target_url}
            attr_selector = {
                '_id': -1, 'id': 1, 'article_url': 1, 'title': 1,
                'published_date': 1, 'author': 1, 'type': 1}
            target = db.articles.find_one(query, attr_selector) \
                or db.blog_posts.find_one(query, attr_selector)

            if target is None:
                continue

            # graph[source_url].add(target_url)

            g.add_node(
                source['id'], **{k.replace('_', ''): source[k] for k in attr_keys if not source[k] is None})
            g.add_node(
                target['id'], **{k.replace('_', ''): target[k] for k in attr_keys if not target[k] is None})
            g.add_edge(source['id'], target['id'])

            edge_count += 1

    doc_count += 1

    if doc_count % 1000 == 0:
        logging.info("%d documents processed (%d edges created)" % (doc_count, edge_count))

logging.info("%d documents processed (%d edges created)" % (doc_count, edge_count))


logging.info("Saving graph to %s" % output_graph_path)
if output_graph_path.endswith('.gml') or output_graph_path.endswith('.gml.gz'):
    nx.write_gml(g, output_graph_path)
else:
    nx.write_graphml(g, output_graph_path)
