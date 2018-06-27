import json
import logging
import os
import urllib.parse
from enum import Enum

import yaml
from SPARQLWrapper import SPARQLWrapper, JSON
from joblib import Memory
from pymongo import MongoClient

logger = logging.getLogger(__name__)

dbpedia_sparql_url = 'https://dbpedia.org/sparql'
memory = Memory(cachedir='/opt/army-ant/cache/dbpedia', compress=9, verbose=0, bytes_limit=1 * 1024 * 1024 * 1024)
#memory = Memory(cachedir='/dev/shm/army-ant/cache/dbpedia', verbose=0, bytes_limit=5 * 1024 * 1024 * 1024)


class DBpediaClass(Enum):
    person = 'dbo:Person'
    organization = 'dbo:Organisation'
    place = 'dbo:Place'

#
# SPARQL API
#

@memory.cache
def fetch_dbpedia_entity_labels(dbpedia_class, offset=None, limit=None):
    sparql = SPARQLWrapper(dbpedia_sparql_url)

    query = '''
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT DISTINCT (STR(?entityLabel) AS ?label)
        WHERE {
          ?entity a %s .
          ?entity rdfs:label ?entityLabel .
          FILTER (langMatches(lang(?entityLabel), 'en'))
        }
    ''' % dbpedia_class.value
    if offset: query += 'OFFSET %d\n' % offset
    if limit:  query += 'LIMIT %d' % limit

    #print(query)
    sparql.setQuery(query)

    sparql.setReturnFormat(JSON)
    result = sparql.query()
    data = result.response.read()
    #print(data.decode('utf-8'))
    data = json.loads(data.decode('utf-8'))

    entities = set([])
    for binding in data['results']['bindings']:
        entity = binding['label']['value']
        entities.add(entity)

    return list(entities)

def fetch_dbpedia_triples(entity_labels, ignored_properties=None):
    """
    Fetch all DBpedia triples for the entities with the given labels (in English),
    while individually caching triples per entity and ensuring only a single HTTP
    request is done for the whole list of entities.
    """

    config = yaml.load(open('config.yaml'))
    db_config = config.get('defaults', {}).get('db', {})
    if db_config.get('type', 'mongo') != 'mongo': db_config = {}

    host = db_config.get('location', 'localhost')
    db_name = db_config.get('name', 'army_ant')

    mongo = MongoClient(host)

    cache = mongo[db_name]['entity_triples']
    cache.create_index('label')

    if ignored_properties is None:
        ignored_properties = ['http://dbpedia.org/ontology/wikiPageWikiLink']

    triples = set([])

    entity_uris = set([])
    for entity_label in entity_labels:
        cached_entity = cache.find_one({ 'label': entity_label })
        if cached_entity:
            s = (cached_entity['uri'], cached_entity['label'])
            for triple in cached_entity['triples']:
                p = (triple['predicate']['uri'], triple['predicate']['label'])
                o = (triple['object']['uri'], triple['object']['label'])
                triples.add((s, p, o))
        else:
            entity_uris.add('<http://dbpedia.org/resource/%s>' % urllib.parse.quote_plus(entity_label.replace(' ', '_')))

    if len(entity_uris) == 0: return triples

    sparql = SPARQLWrapper(dbpedia_sparql_url)

    query = '''
            SELECT ?s ?sLabel ?p ?pLabel ?o ?oLabel
            WHERE {
              VALUES ?s { %s }
              ?s ?p ?o .
              ?s rdfs:label ?sLabel .
              ?p rdfs:label ?pLabel .
              ?o rdfs:label ?oLabel .
              FILTER (langMatches(lang(?sLabel), 'en')
                && langMatches(lang(?pLabel), 'en')
                && langMatches(lang(?oLabel), 'en'))
            }
        ''' % ' '.join(entity_uris)

    # print(query)
    sparql.setQuery(query)

    sparql.setReturnFormat(JSON)
    result = sparql.query()
    data = result.response.read()
    # print(data.decode('utf-8'))
    data = json.loads(data.decode('utf-8'))

    cache_data = {}

    for binding in data['results']['bindings']:
        if ignored_properties and binding['p']['value'] in ignored_properties: continue

        s = (binding['s']['value'], binding['sLabel']['value'])
        p = (binding['p']['value'], binding['pLabel']['value'])
        o = (binding['o']['value'], binding['oLabel']['value'])

        if not s in cache_data: cache_data[s] = []

        cache_data[s].append({
            'predicate': { 'uri': p[0], 'label': p[1] },
            'object': { 'uri': o[0], 'label': o[1] }
        })

        triples.add((s, p, o))

    for k, v in cache_data.items():
        cache.insert({
            'uri': k[0],
            'label': k[1],
            'triples': v
        })

    return list(triples)

if __name__ == '__main__':
    dbpedia_triples = fetch_dbpedia_triples(["Mr.", "Ames, Iowa", "Barack Obama", "Portugal"])
    for (s, sl), (p, pl), (o, ol) in dbpedia_triples:
        print('%20s %20s %50s' % (sl, pl, ol))