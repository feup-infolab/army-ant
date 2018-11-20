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
visiting_node = starting_node
prev_visited_len = 0
continuous_stagnant_steps = 0
visited = set([])

try:
    while len(visited) < n:
        print("==> Visiting node:", visiting_node)

        response = requests.get(urllib.parse.urljoin('https://en.wikipedia.org/wiki/', visiting_node))
        soup = BeautifulSoup(response.text, 'html.parser')

        current = url_to_title(response.url)
        links = set(
            url_to_title(a.attrs['href'])
            for a in soup.find_all(article_wiki_anchor))

        for link in links:
            g.add_edge(current, link)

        prev_visited_len = len(visited)
        visited.add(current)

        if prev_visited_len == len(visited):
            continuous_stagnant_steps += 1
        else:
            continuous_stagnant_steps = 0

        if prev_visited_len == len(visited) and continuous_stagnant_steps > 5:
            starting_node = visiting_node = np.random.choice(list(links))
            print("    Switched starting node to %s" % starting_node)
        elif np.random.random() <= 0.85:
            visiting_node = np.random.choice(list(links))
        else:
            visiting_node = starting_node

        print("    stagnant = %d" % continuous_stagnant_steps)
        print("    |V| = %d" % g.number_of_nodes())
        print("    |E| = %d" % g.number_of_edges())

    print("==> Saving graph to %s" % path)
    nx.write_graphml(g, path)
except KeyboardInterrupt:
    print("\nCtrl+C received...")

    try:
        while True:
            answer = input("Save collected graph? [yn] ").lower()
            if not answer in ('y', 'n'): continue
            if answer == 'y':
                print("==> Saving graph with |V| = %d and |E| = %d to %s" % (
                    g.number_of_nodes(), g.number_of_edges(), path))
                nx.write_graphml(g, path)
            else:
                print("==> Collected graph discarded")
            break
    except KeyboardInterrupt:
        print("\n==> Collected graph discarded")
