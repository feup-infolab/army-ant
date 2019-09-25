import logging
import os
import re
import sys
import time

import pandas as pd

from army_ant.reader import Document, Entity, MongoDBReader
from army_ant.setup import config_logger
from army_ant.util.dbpedia import fetch_dbpedia_triples
from army_ant.util.text import AhoCorasickEntityExtractor

logger = logging.getLogger(__name__)


class TRECWashingtonPostReader(MongoDBReader):
    def __init__(
            self, source_path, features_location=None, include_ae_doc_profile=False,
            include_dbpedia=False, limit=None):
        super(TRECWashingtonPostReader, self).__init__(source_path)

        self.ac_ner = None

        self.articles = self.db.articles.find({}, no_cursor_timeout=True)
        self.blog_posts = self.db.blog_posts.find({}, no_cursor_timeout=True)

        self.features_location = features_location
        self.include_ae_doc_profile = include_ae_doc_profile
        self.include_dbpedia = include_dbpedia
        self.limit = limit
        self.counter = 0

        if include_ae_doc_profile:
            ignored_features = ['Language', 'NamedEntities', 'SentimentAnalysis', 'EmotionCategories']

            logger.info("Loading and preprocessing features from Antonio Espejo's document profile")
            self.features = pd.read_csv(os.path.join(self.features_location, 'features.tsv.gz'),
                                        sep='\t', index_col='id', na_filter=False, compression='gzip')
            for ignored_feature in ignored_features:
                del self.features[ignored_feature]

    def to_plain_text(self, doc, limit=None):
        paragraphs = []

        for content in doc['contents']:
            if content and 'subtype' in content and content['subtype'] == 'paragraph':
                text = re.sub(r'<.*?>', ' ', content['content'])
                paragraphs.append(text)
                if limit and len(paragraphs) >= limit:
                    break

        return '\n\n'.join(paragraphs)

    def to_wikipedia_entity(self, entity):
        return Entity(entity, "http://en.wikipedia.org/wiki/%s" % entity.replace(' ', '_'))

    def to_washington_post_author_entity(self, author_name):
        return Entity(
            author_name,
            'https://www.washingtonpost.com/people/%s' % (author_name.lower().replace(' ', '-')))

    def parse_feature_array(self, feature_value, dicretized_version=False):
        if dicretized_version:
            if feature_value == 'null':
                return []
            return feature_value.split('|')
        else:
            parts = feature_value.split('~¨-*', 1)
            if len(parts) >= 1:
                parts = re.split(r',\s+', parts[1][1:-1])
                a = []
                for part in parts:
                    v, w = part.split(';', 1)
                    a.append((v[1:-1], float(w)))
                return a

    def build_triples(self, doc):
        entities = set([])
        triples = set([])

        if not self.include_ae_doc_profile and not self.include_dbpedia:
            return list(entities), list(triples)

        if self.ac_ner is None:
            self.ac_ner = AhoCorasickEntityExtractor("/opt/army-ant/gazetteers/all.txt")

        doc_id = doc['id']
        text = self.to_plain_text(doc, limit=3)
        entities = entities.union(Entity(entity_name) for entity_name in self.ac_ner.extract(text))
        entities.add(self.to_washington_post_author_entity(doc['author']))

        if self.include_ae_doc_profile:
            doc_features = self.features.loc[doc['id']]
            for feature_name in doc_features.index:
                if feature_name == 'Keywords':
                    # feature_values = sorted(self.parse_feature_array(
                    #     doc_features[feature_name]), key=lambda kw: kw[1])
                    # feature_values = [k for k, _ in feature_values[0:5]]
                    feature_values = self.parse_feature_array(doc_features[feature_name], dicretized_version=True)
                elif feature_name == 'ReadingComplexity':
                    feature_values = [doc_features[feature_name].split('~', 1)[0]]
                elif feature_name == 'EmotionCategories':
                    # feature_values = sorted(self.parse_feature_array(
                    #     doc_features[feature_name]), key=lambda kw: kw[1])
                    # feature_values = [k for k, w in feature_values if w >= 0.5]
                    feature_values = self.parse_feature_array(doc_features[feature_name], dicretized_version=True)
                else:
                    feature_values = [doc_features[feature_name]]

                if feature_values is None or len(feature_values) == 0:
                    continue

                for feature_value in feature_values:
                    entities.add(Entity(feature_value))

        if self.include_dbpedia:
            logger.debug("Fetching DBpedia triples for %d entities in document %s" % (len(entities), doc_id))

            max_retries = 10

            retries_left = max_retries
            retry_wait = 0

            while True:
                try:
                    dbpedia_triples = list(fetch_dbpedia_triples([entity.label for entity in entities]))
                    break
                except Exception:
                    if retries_left > 0:
                        retry_wait += 10 * (max_retries - retries_left + 1)
                        logger.exception(
                            "Error retrieving triples for %d entities in document %s, retrying in %d seconds"
                            " (%d retries left)" % (len(entities), doc_id, retry_wait, retries_left))
                        retries_left -= 1
                        time.sleep(retry_wait)
                    else:
                        logger.exception(
                            "Could not retrieve triples for %d entities in document %s, giving up (returning "
                            "%d cached triples)" % (len(entities), doc_id, len(triples)))
                        dbpedia_triples = []
                        break

            for (s, sl), (p, pl), (o, ol) in dbpedia_triples:
                triples.add((
                    Entity(sl, s),
                    Entity(pl, p),
                    Entity(ol, o)
                ))

        return list(entities), list(triples)

    def __next__(self):
        if self.limit is not None and self.counter >= self.limit:
            raise StopIteration

        try:
            doc = next(self.articles)
        except StopIteration:
            self.articles.close()
            doc = next(self.blog_posts)

        if doc:
            logger.debug("Reading %s" % doc['id'])

            text = self.to_plain_text(doc)
            entities, triples = self.build_triples(doc)

            self.counter += 1

            return Document(
                doc_id=doc['id'],
                title=doc['title'],
                text=text,
                entities=entities,
                triples=triples,
                metadata={'url': doc['article_url'], 'name': doc['title']})

        self.blog_posts.close()
        self.client.close()
        raise StopIteration


if __name__ == '__main__':
    config_logger(logging.DEBUG)

    r = TRECWashingtonPostReader(
        'wapo_sample', features_location='/opt/army-ant/features/wapo-sample', include_ae_doc_profile=True)
    c = 0
    for doc in r:
        print(doc)
        c += 1
        if c % 10 == 0:
            sys.exit(0)
