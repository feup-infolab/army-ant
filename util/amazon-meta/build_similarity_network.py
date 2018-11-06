#!/usr/bin/env python
#
# build_similarity_graph.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-11-06

import networkx as nx
import sys

from enum import Enum


class Group(Enum):
    baby_product = 'Baby Product'
    book = 'Book'
    ce = 'CE'
    dvd = 'DVD'
    music = 'Music'
    software = 'Software'
    sports = 'Sports'
    toy = 'Toy'
    video = 'Video'
    video_games = 'Video Games'


class Item(object):
    def __init__(self, id, asin, title, group, sales_rank, similar, categories, reviews, avg_rating):
        self.id = id
        self.asin = asin
        self.title = title
        self.group = group
        self.sales_rank = sales_rank
        self.similar = similar
        self.categories = categories
        self.reviews = reviews
        self.avg_rating = avg_rating


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: %s INPUT_DATASET OUTPUT_GML_GZ" % sys.argv[0])
        sys.exit(1)

