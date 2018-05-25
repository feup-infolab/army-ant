import gzip
import logging
import re
import sys
from enum import Enum

import rdflib
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from joblib import Memory

from army_ant.setup import config_logger

logger = logging.getLogger(__name__)

wikidata_api_url = 'https://www.wikidata.org/w/api.php'
memory = Memory(cachedir='/opt/army-ant/cache/wikidata', verbose=0, bytes_limit=500 * 1024 * 1024)


class WikidataClass(Enum):
    human = 'wd:Q5'
    organization = 'wd:Q43229'
    location = 'wd:Q17334923'


def entity_to_triples(entity, filter_props=None):
    if filter_props is None: filter_props = ['ID', 'Id', 'Commons', 'image', 'equivalent']

    triples = []

    entity_label = entity.get('labels', {}).get('en', {}).get('value')
    if entity_label is None: return []

    for prop, claim in entity.get('claims', []).items():
        if len(claim) <= 0: continue
        datavalue = claim[0].get('mainsnak', {}).get('datavalue', {})
        datavalue_type = datavalue.get('type')
        datavalue_value = datavalue.get('value')
        if datavalue_type == 'string':
            if entity_label == datavalue_type: continue
            props = get_entities([prop])
            if not prop in props: continue
            prop_label = props[prop].get('labels', {}).get('en', {}).get('value')
            if filter_props and any([filter_prop in prop_label for filter_prop in filter_props]): continue
            if datavalue_value is None: continue
            triples.append((entity_label, prop_label, datavalue_value))

    return triples


#
# MediaWiki API
#

@memory.cache
def search_entities(search):
    response = requests.get(wikidata_api_url, {
        'action': 'wbsearchentities',
        'language': 'en',
        'format': 'json',
        'search': search
    })

    if response.status_code == requests.codes.ok:
        json = response.json()
        if 'search' in json and len(json['search']) > 0:
            return json['search']

        return []


@memory.cache
def get_entities(ids):
    response = requests.get(wikidata_api_url, {
        'action': 'wbgetentities',
        'props': 'labels|claims',
        'languages': 'en',
        'format': 'json',
        'ids': '|'.join(ids)
    })

    if response.status_code == requests.codes.ok:
        json = response.json()
        return json.get('entities', {})

    return {}


#
# SPARQL API
#

@memory.cache
def fetch_wikidata_entity_labels(wikidata_class, offset=None, limit=None):
    sparql = SPARQLWrapper('https://query.wikidata.org/sparql')

    query = '''
        SELECT DISTINCT (STR(?entityLabel) AS ?label)
        WHERE {
          ?entity (wdt:P31/wdt:P279*) %s .
          ?entity rdfs:label ?entityLabel .
          FILTER (langMatches(lang(?entityLabel), 'en'))
        }
    ''' % wikidata_class.value
    if offset: query += 'OFFSET %d\n' % offset
    if limit:  query += 'LIMIT %d' % limit

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    json = sparql.query().convert()

    entities = []
    for binding in json['results']['bindings']:
        entity = binding['label']['value']
        entities.append(entity)
    return entities


@memory.cache
def fetch_wikidata_entity_subclasses(wikidata_class, include_self=True):
    sparql = SPARQLWrapper('https://query.wikidata.org/sparql')

    query = '''
        SELECT DISTINCT (STR(?entityType) AS ?type)
        WHERE {
            ?entity wdt:P31 ?entityType.
            ?entityType wdt:P279%s %s .
        }
    ''' % ('*' if include_self else '+', wikidata_class.value)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    json = sparql.query().convert()

    entities = []
    for binding in json['results']['bindings']:
        entity = binding['type']['value']
        entities.append('<%s>' % entity)
    return entities


#
# Dump processing
#

def get_wikidata_dump_entity_labels(dump_location, wikidata_class):
    g = rdflib.Graph()
    g.parse(gzip.open(dump_location, 'r'), format='nt')

    res = g.query('''
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/> 
        
        SELECT DISTINCT (STR(?entityLabel) AS ?label)
        WHERE {
            ?entity wdt:P31 %s .
            ?entity rdfs:label ?entityLabel .
            FILTER (langMatches(lang(?entityLabel), 'en'))
        }
    ''' % WikidataClass[wikidata_class].value)

    return [row[0] for row in res]


entity_regex = re.compile('<(.*?)>')
literal_regex = re.compile('"(.*?)"@([^ .]+)')
blank_node_regex = re.compile('_:([^ ]+)')
n_triple_regex = re.compile(r'(?P<subject>%s|%s|%s) (?P<predicate>%s|%s|%s) (?P<object>%s|%s|%s)' % (
    entity_regex.pattern, literal_regex.pattern, blank_node_regex.pattern,
    entity_regex.pattern, literal_regex.pattern, blank_node_regex.pattern,
    entity_regex.pattern, literal_regex.pattern, blank_node_regex.pattern))


def parse_n_triple(line):
    m = n_triple_regex.match(line.strip())
    if m: return m.groupdict()


def filter_entities_by_class(wikidata_dump_location, class_uris):
    entities = []
    print_count = 0
    with gzip.open(wikidata_dump_location, 'rt') as f:
        for line in f:
            triple = parse_n_triple(line)
            if triple is None: continue
            s, p, o = triple['subject'], triple['predicate'], triple['object']
            if p == '<http://www.wikidata.org/prop/direct/P31>' and o in class_uris:
                entities.append(s)

            if len(entities) % 1000 == 0 and print_count < len(entities):
                logger.info("%d entities found so far" % len(entities))
                print_count = len(entities)
                if print_count >= 5000: break
    return entities


def get_label_for_entity_uris(wikidata_dump_location, entity_uris, language='en'):
    entity_labels = {}
    line_count = 0
    with gzip.open(wikidata_dump_location, 'rt') as f:
        for line in f:
            triple = parse_n_triple(line)
            if triple is None: continue
            s, p, o = triple['subject'], triple['predicate'], triple['object']
            for entity_uri in entity_uris:
                logger.info("Finding label ")
                if s == entity_uri and p == '<http://www.w3.org/2000/01/rdf-schema#label>':
                    m = literal_regex.match(o)
                    if m and m.group(2)[0:2] == language: entity_labels[entity_uri] = m.group(1)
    return entity_labels


if __name__ == '__main__':
    config_logger()

    if len(sys.argv) < 2:
        print("Usage: %s N_TRIPLE_LINE" % sys.argv[0])
        sys.exit(1)

    parse_n_triple(sys.argv[1])
