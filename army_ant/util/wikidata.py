import json
import re
import sys

import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from joblib import Memory

from army_ant.setup import config_logger

wikidata_api_url = 'https://www.wikidata.org/w/api.php'
memory = Memory(cachedir='/opt/army-ant/cache/wikidata', verbose=0, bytes_limit=500*1024*1024)


# @functools.lru_cache(maxsize=1000)
@memory.cache
def get_entity_id_by_name(name):
    response = requests.get(wikidata_api_url, {
        'action': 'wbsearchentities',
        'language': 'en',
        'format': 'json',
        'search': name
    })
    if response.status_code == requests.codes.ok:
        json = response.json()
        if 'search' in json and len(json['search']) > 0:
            return json['search'][0]['id']


@memory.cache
def get_entity_by_id(id):
    response = requests.get(wikidata_api_url, {
        'action': 'wbgetentities',
        'props': 'labels|claims',
        'languages': 'en',
        'format': 'json',
        'ids': id
    })
    if response.status_code == requests.codes.ok:
        json = response.json()
        return json.get('entities', {}).get(id, {})
    return []


def entity_to_triples(entity, filter_props=None):
    if filter_props is None: filter_props = ['ID', 'Id', 'Commons', 'image', 'equivalent']

    entity_label = entity.get('labels', {}).get('en', {}).get('value')
    if entity_label is None: return []

    triples = []
    for prop, claim in entity.get('claims', []).items():
        if len(claim) <= 0: continue
        datavalue = claim[0].get('mainsnak', {}).get('datavalue', {})
        datavalue_type = datavalue.get('type')
        datavalue_value = datavalue.get('value')
        if datavalue_type == 'string':
            if entity_label == datavalue_type: continue
            prop_label = get_entity_by_id(prop).get('labels', {}).get('en', {}).get('value')
            if filter_props and any([filter_prop in prop_label for filter_prop in filter_props]): continue
            if datavalue_value is None: continue
            triples.append((entity_label, prop_label, datavalue_value))

    return triples


def get_entity_triples_by_name(name):
    id = get_entity_id_by_name(name)
    entity = get_entity_by_id(id)
    return entity_to_triples(entity)


if __name__ == '__main__':
    config_logger()

    if len(sys.argv) < 2:
        print("Usage: %s ENTITY_NAME" % sys.argv[0])
        sys.exit(1)

    id = get_entity_id_by_name(sys.argv[1])
    print(id)

    entity = get_entity_by_id(id)
    print(json.dumps(entity, indent=4))

    triples = entity_to_triples(entity)
    for triple in triples:
        print(triple)


@memory.cache
def fetch_wikidata_entities(class_label, offset, limit):
    class_label_to_uri = {
        'person': 'wd:Q215627',
        'organization': 'wd:Q43229',
        'geographic location': 'wd:Q2221906'
    }

    assert class_label in class_label_to_uri, "Class label %s not supported" % class_label

    sparql = SPARQLWrapper('https://query.wikidata.org/sparql')
    query = '''
        SELECT ?entityLabel
        WHERE {
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en" }
          ?entity (wdt:P31/wdt:P279*) %s
        }
        OFFSET %d
        LIMIT %d
    ''' % (class_label_to_uri[class_label], offset, limit)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    response = sparql.query().convert()

    entities = []
    for binding in response['results']['bindings']:
        entity = binding['entityLabel']['value']
        if re.match(r'^Q\d+$', entity): continue # skip unlabeled entities
        entities.append(entity)
    return entities