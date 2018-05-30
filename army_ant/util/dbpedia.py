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
    organization = 'dbo:Organization'
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

    entities = []
    for binding in data['results']['bindings']:
        entity = binding['label']['value']
        entities.append(entity)

    return entities
