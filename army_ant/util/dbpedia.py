import json
import logging
from enum import Enum

from SPARQLWrapper import SPARQLWrapper, JSON
from joblib import Memory

logger = logging.getLogger(__name__)

dbpedia_sparql_url = 'https://dbpedia.org/sparql'
memory = Memory(cachedir='/opt/army-ant/cache/dbpedia', verbose=0, bytes_limit=500 * 1024 * 1024)


class DBpediaClass(Enum):
    person = 'dbo:Person'
    organization = 'dbo:Organisation' \
                   ''
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

@memory.cache
def fetch_dbpedia_triples(entity_name, ignored_properties=None):
    if ignored_properties is None:
        ignored_properties = ['http://dbpedia.org/ontology/wikiPageWikiLink']
        logger.warning("Using default list of ignored properties: %s" % ', '.join(ignored_properties))

    sparql = SPARQLWrapper(dbpedia_sparql_url)

    query = '''
            PREFIX dbr: <http://dbpedia.org/resource/>
            SELECT ?s ?sLabel ?p ?pLabel ?o ?oLabel
            WHERE {
              VALUES ?s { dbr:%s }
              ?s ?p ?o .
              ?s rdfs:label ?sLabel .
              ?p rdfs:label ?pLabel .
              ?o rdfs:label ?oLabel .
              FILTER (langMatches(lang(?sLabel), 'en')
                && langMatches(lang(?pLabel), 'en')
                && langMatches(lang(?oLabel), 'en'))
            }
        ''' % entity_name.replace(' ', '_')

    # print(query)
    sparql.setQuery(query)

    sparql.setReturnFormat(JSON)
    result = sparql.query()
    data = result.response.read()
    # print(data.decode('utf-8'))
    data = json.loads(data.decode('utf-8'))

    triples = set([])
    for binding in data['results']['bindings']:
        if binding['p']['value'] in ignored_properties: continue

        s = (binding['s']['value'], binding['sLabel']['value'])
        p = (binding['p']['value'], binding['pLabel']['value'])
        o = (binding['o']['value'], binding['oLabel']['value'])

        triples.add((s, p, o))

    return list(triples)

if __name__ == '__main__':
    fetch_dbpedia_triples("Barack Obama")