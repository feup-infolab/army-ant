import functools
import json

import requests
import wikidata.client


@functools.lru_cache(maxsize=1000)
def get_entity_id_by_name(name):
    response = requests.get(
        'https://www.wikidata.org/w/api.php?action=wbsearchentities&language=en&format=json&search=%s' % name)
    if response.status_code == requests.codes.ok:
        json = response.json()
        if 'search' in json and len(json['search']) > 0:
            return json['search'][0]['id']


@functools.lru_cache(maxsize=1000)
def get_entity_by_id(id):
    client = wikidata.client.Client()
    return client.get(id, load=True)

def entity_to_triples(entity):
    print(json.dumps(entity.data, indent=4))
    label = entity.data.get('labels', {})['en']['value']
    triples = []
    triples.append((label, 'related_to', label))
    return triples

if __name__ == '__main__':
    id = get_entity_id_by_name('Logan Thomas')
    print(id)
    #entity = get_entity_by_id(id)
    #print(entity_to_triples(entity))
