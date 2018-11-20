#!/usr/bin/env python
#
# rw_sample_link_graph.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-11-20
#
# Random walk sampling of the Wikipedia links graph, as defined in:
#
# Leskovec, J. & Faloutsos, C. Sampling from large graphs. Proceedings of the Twelfth ACM SIGKDD International
# Conference on Knowledge Discovery and Data Mining, Philadelphia, PA, USA, August 20-23, 2006, 2006 , 631-636
#

import re
import sys
import urllib.parse

import networkx as nx
import numpy as np
import requests
import requests_cache
from bs4 import BeautifulSoup

# Some Wikipedia URLs have slashes, e.g., https://en.wikipedia.org/wiki/Maxi_Sandal_2003_/_Moonlight
url_title_regex = re.compile(r'.*/wiki/([^ #?]+)')


def url_to_title(url):
    match = url_title_regex.match(urllib.parse.unquote(url))
    if match:
        return match.group(1)


def article_wiki_anchor(tag):
    return tag.name == 'a' and tag.has_attr('href') and \
        tag.attrs['href'].startswith("/wiki") and not ":" in tag.attrs['href']


if len(sys.argv) < 3:
    print("Usage: %s NUMBER_OF_VISITED_NODES GRAPHML_GZ_PATH [CACHE_PATH]" % sys.argv[0])
    sys.exit(1)

n = int(sys.argv[1])
path = str(sys.argv[2])

if len(sys.argv) > 3:
    cache_path = sys.argv[3]
    print("==> Using cache at %s" % cache_path)
    requests_cache.install_cache(cache_path)

g = nx.DiGraph()

starting_node = requests.head('https://en.wikipedia.org/wiki/Special:Random', allow_redirects=True).url
seed = starting_node
prev_visited_len = 0
retries = 0
visited = set([])

while len(visited) < n:
    print("==> Seed node:", seed)

    response = requests.get(urllib.parse.urljoin('https://en.wikipedia.org/wiki/', seed))
    soup = BeautifulSoup(response.text, 'html.parser')

    current = url_to_title(response.url)
    links = set(
        url_to_title(a.attrs['href'])
        for a in soup.find_all(article_wiki_anchor))

    for link in links:
        g.add_edge(current, link)

    prev_visited_len = len(visited)
    visited.add(current)

    if prev_visited_len == len(visited) and retries > 10:
        starting_node = seed = np.random.choice(list(links))
        print("    Switched starting node to %s" % starting_node)
    elif np.random.random() <= 0.85:
        seed = np.random.choice(list(links))
    else:
        seed = starting_node
        retries = 0

    if prev_visited_len == len(visited): retries += 1

    print("    retries = %d" % retries)
    print("    |V| = %d" % g.number_of_nodes())
    print("    |E| = %d" % g.number_of_edges())

print("==> Saving graph to %s" % path)
nx.write_graphml(g, path)
