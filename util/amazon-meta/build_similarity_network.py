#!/usr/bin/env python
#
# build_similarity_graph.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-11-06

import networkx as nx
import sys

from dataclasses import dataclass
from enum import Enum

# Requires Python 3.7.x (install it with pyenv)
@dataclass
class Item(object):
    id: int
    asin: str
    title: str
    group: Group
    sales_rank: int
    similar: List[int]
    categories: List[Category]
    reviews: List[Review]
    avg_rating: float

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

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: %s INPUT_DATASET OUTPUT_GML_GZ" % sys.argv[0])
        sys.exit(1)

