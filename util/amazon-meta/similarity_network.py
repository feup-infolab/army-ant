#!/usr/bin/env python
#
# similarity_graph.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-11-06

import networkx as nx
import sys, os, gzip, datetime, itertools, re

from enum import Enum
from lark import Lark, Transformer, Tree


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


class Product:
    def __init__(self, id, asin, title, group, sales_rank, similar, categories, reviews, avg_rating):        
        self.id = int(id)
        self.asin = str(asin)
        self.title = str(title)

        assert type(group) is Group
        self.group = group

        self.sales_rank = int(sales_rank)
        
        assert type(similar) is list
        if len(similar) > 0: assert type(similar[0]) is str or type(similar[0]) is Product
        self.similar = similar

        assert type(categories) is list
        if len(categories) > 0: assert type(categories[0]) is Category
        self.categories = categories

        assert type(reviews) is list
        if len(reviews) > 0: assert type(reviews[0]) is Review
        self.reviews = reviews

        self.avg_rating = float(avg_rating)

    def basic_attributes(self):
        return {
            'id': self.id,
            'asin': self.asin,
            'title': self.title,
            'group': self.group.name,
            'salesrank': self.sales_rank,
            'avgrating': self.avg_rating
        }

    def __repr__(self):
        return "product\n" \
            "\tid\t%d\n" \
            "\tasin\t%s\n" \
            "\ttitle\t%s\n" \
            "\tgroup\t%s\n" \
            "\tsales_rank\t%d\n" \
            "\tsimilar\t%s\n" \
            "\tcategories\t%s\n" \
            "\treviews\t%s\n" \
            "\tavg_rating\t%f\n" % (
                self.id,
                self.asin,
                self.title,
                self.group,
                self.sales_rank,
                self.similar,
                self.categories,
                self.reviews,
                self.avg_rating)


class Category:
    def __init__(self, category_id, name, sub_category=None):
        self.category_id = int(category_id)
        self.name = str(name)
        assert type(sub_category) is Category or sub_category is None
        self.sub_category = sub_category

    def __repr__(self):
        base_repr = "%s[%d]" % (self.name, self.category_id)
        if self.sub_category:
            return "%s->%s" % (base_repr, repr(self.sub_category))
        return base_repr


class Review:
    def __init__(self, date, user_id, rating, votes, helpful):
        assert type(date) is datetime.date
        self.date = date
        self.user_id = str(user_id)
        self.rating = int(rating)
        self.votes = int(votes)
        self.helpful = int(helpful)

    def __repr__(self):
        return "Review(%s, %s, %d, %d, %d)" % (self.user_id, self.date, self.rating, self.votes, self.helpful)


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


product_parser = Lark(open(os.path.join(__location__, 'product_parser.lark')).read())


def list_to_category_hierarchy(cat_lst):
    for cat_a, cat_b in zip(cat_lst, cat_lst[1:]):
        cat_a.sub_category = cat_b
    return cat_lst[0]


class ProductTransformer(Transformer):
    start = dict
    discontinued_product = lambda self, t: ('product', {})
    product = lambda self, lst: ('product', dict(lst))

    id = lambda self, t: ('id', int(t[0].value))

    asin_value = lambda self, t: t[0]
    asin = lambda self, t: ('asin', t[0].value)

    title = lambda self, t: ('title', t[0].value)
    group = lambda self, t: ('group', Group(t[0].value))
    sales_rank = lambda self, t: ('sales_rank', int(t[0].value))
    
    similar = lambda self, lst: ('similar', lst[1][0:-1] if lst and len(lst) > 1 else [])
    similar_count = lambda self, t: ('count', int(t[0].value))
    similar_asins = lambda self, t: [d.value for d in t]

    categories = lambda self, lst: ('categories', lst[1][0:-1] if lst and len(lst) > 1 else [])
    category_count = lambda self, t: ('count', int(t[0].value))
    unnamed_category = lambda self, _: Category(-1, "Unknown")
    category_hierarchies = list
    category_hierarchy = lambda self, lst: list_to_category_hierarchy(lst[0:-1])
    category = lambda self, c: Category(c[1].value, c[0].value)

    reviews = lambda self, t: ('reviews', dict(t))
    
    review_summary = lambda self, lst: ('summary', dict(lst[0:-1]) if lst and len(lst) > 0 else {})
    review_total = lambda self, t: ('total', int(t[0].value))
    review_downloaded = lambda self, t: ('downloaded', int(t[0].value))
    review_avg_rating = lambda self, t: ('avg_rating', float(t[0].value))
    
    review_items = lambda self, lst: ('items', lst)
    review = lambda self, lst: Review(**dict(lst[0:-1]))
    date = lambda self, t: ('date', datetime.datetime.strptime(t[0].value, '%Y-%m-%d').date())
    customer = lambda self, t: ('user_id', t[0].value)
    rating = lambda self, t: ('rating', int(t[0].value))
    votes = lambda self, t: ('votes', int(t[0].value))
    helpful = lambda self, t: ('helpful', int(t[0].value))


# XXX Unfortunately, the Lark grammar doesn't work as it should when there are too many reviews
# def parse_product(data):
#     tree = product_parser.parse(data)
#     tree = ProductTransformer().transform(tree)

#     if tree['product']:
#         return Product(
#             id = tree['id'],
#             asin = tree['asin'],
#             title = tree['product']['title'],
#             group = tree['product']['group'],
#             sales_rank = tree['product']['sales_rank'],
#             similar = tree['product']['similar'],
#             categories = tree['product']['categories'],
#             reviews = tree['product']['reviews']['items'],
#             avg_rating = tree['product']['reviews']['summary']['avg_rating'])


# The fucking parser took me the whole day to code... This only took me 30 mins. #FML
def parse_product(data):
    data = data.split("\n")
    product = {}
    for line in data:
        line = line.strip()
        
        if line.startswith('Id:'):
            _, id = re.split(r'\s+', line)
            product['id'] = int(id)
            print("==> Parsing product %d" % product['id'])
        
        elif line.startswith('ASIN:'):
            _, asin = re.split(r'\s+', line)
            product['asin'] = asin

        elif line == 'discontinued product':
            return
        
        elif line.startswith('title:'):
            _, title = re.split(r'\s+', line, 1)
            product['title'] = title
        
        elif line.startswith('group:'):
            _, group = re.split(r'\s+', line, 1)
            product['group'] = Group(group)
        
        elif line.startswith('salesrank:'):
            _, sales_rank = re.split(r'\s+', line, 1)
            product['sales_rank'] = int(sales_rank)
        
        elif line.startswith('similar:'):
            similar = re.split(r'\s+', line)
            product['similar'] = similar[2:]
        
        elif line.startswith('|'):
            category_strs = line.split('|')[1:]
            categories = []
            for category_str in category_strs:
                m = re.match(r'(.*)\[(\d+)\]', category_str)
                if m:
                    categories.append(Category(int(m.group(2)), m.group(1)))
            if not 'categories' in product:
                product['categories'] = []
            product['categories'].append(list_to_category_hierarchy(categories))

        elif line.startswith("reviews"):
            m = re.match(r'.*avg rating:\s+(\d+(?:\.\d+)?)', line)
            if m:
                product['avg_rating'] = float(m.group(1))

        elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', line):
            m = re.match(
                r'(\d{4}-\d{1,2}-\d{1,2})\s+cutomer:\s+([^ ]+)\s+rating:\s+(\d+)\s+votes:\s+(\d+)\s+helpful:\s+(\d+)',
                line)
            if m:
                review = Review(
                    datetime.datetime.strptime(m.group(1), '%Y-%m-%d').date(),
                    m.group(2),
                    int(m.group(3)),
                    int(m.group(4)),
                    int(m.group(5))
                )
                if not 'reviews' in product:
                    product['reviews'] = []
                product['reviews'].append(review)

        if not 'categories' in product:
            product['categories'] = []

        if not 'reviews' in product:
            product['reviews'] = []
                
    return Product(**product)


def get_products(path):
    with gzip.open(path, 'rt') as f:
        data = None
        for line in f:
            if line.startswith('Id:'):
                data = line
            elif data:
                if line == '\n':
                    yield parse_product(data)
                else:
                    data += line


def index_products_by_asin(products):
    print("==> Building index by ASIN")
    idx = {}
    for product in products:
        if product:
            idx[product.asin] = product
    print("==> Done building index by ASIN")
    return idx


def resolve_product_similars(products):
    products, it = itertools.tee(products)
    idx = index_products_by_asin(it)

    for product in idx.values():
        print("==> Resolving similar for product %d" % product.id)
        product.similar = filter(lambda p: p, [idx.get(asin) for asin in product.similar if product.similar])
    
    return products


def build_similarity_graph(proucts, path):
    g = nx.Graph()

    for product in products:
        if product is None:
            continue

        print("==> Processing neighborhood of product %d" % product.id)
        g.add_node(product.asin, product.basic_attributes())
        for similar in product.similar:
            g.add_edge(product.asin, similar.asin)

    print("==> Saving graph to %s" % path)
    nx.write_gml(g, path)

    

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: %s INPUT_DATASET OUTPUT_GML_GZ" % sys.argv[0])
        sys.exit(1)

    # products = itertools.islice(get_products(sys.argv[1]), 10)
    products = get_products(sys.argv[1])
    products = resolve_product_similars(products)
    build_similarity_graph(products, sys.argv[2])
    print("==> Done")
