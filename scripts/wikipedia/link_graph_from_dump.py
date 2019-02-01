#!/usr/bin/env python
#
# link_graph_from_dump.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-01-29

import logging
import sys

import mysql.connector as mariadb
import networkx as nx

logging.basicConfig(
    format='%(asctime)s link_graph_from_dump: %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)


if len(sys.argv) < 4:
    print("Usage: %s MYSQL_DBNAME MYSQL_OPTIONS_FILE OUTPUT_GRAPH_PATH" % sys.argv[0])
    sys.exit(1)


database = sys.argv[1]
mycnf_path = sys.argv[2]
output_graph_path = sys.argv[3]


graph = {}

db = mariadb.connect(database=database, option_files=mycnf_path)
c = db.cursor()


logging.info("Loading edges from pagelinks joined with page to obtain titles")

c.execute("""
    SELECT p1.page_title AS source, pl_title AS target
    FROM pagelinks
    JOIN page AS p1 ON pl_from = p1.page_id
    WHERE pl_namespace = 0 AND pl_from_namespace = 0""")

edge_count = 0

for row in c:
    source = row[0].decode('utf-8')
    target = row[1].decode('utf-8')

    if not source in graph:
        graph[source] = []

    graph[source].append(target)

    edge_count += 1
    if edge_count % 100000 == 0:
        logging.info("%d edges read" % edge_count)

logging.info("%d edges read" % edge_count)


logging.info("Converting into networkx format as a DiGraph")
g = nx.DiGraph()
g.add_edges_from((k, v) for k, vs in graph.items() for v in vs)


logging.info("Saving graph to %s" % output_graph_path)
if output_graph_path.endswith('.gml') or output_graph_path.endswith('.gml.gz'):
    nx.write_gml(g, output_graph_path)
else:
    nx.write_graphml(g, output_graph_path)
