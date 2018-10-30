#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import csv
import glob
import itertools
import logging
import os
import re
import shelve
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

import pandas as pd
import requests
import requests_cache
from bs4 import BeautifulSoup, SoupStrainer
from lxml import etree
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from requests.auth import HTTPBasicAuth
from SPARQLWrapper.SPARQLExceptions import EndPointNotFound

from army_ant.exception import ArmyAntException
from army_ant.setup import config_logger
from army_ant.util import get_first, html_to_text, inex
from army_ant.util.dbpedia import fetch_dbpedia_triples
from army_ant.util.text import AhoCorasickEntityExtractor

logger = logging.getLogger(__name__)


class Reader(object):
    @staticmethod
    def factory(source_path, source_reader, features_location=None, limit=None):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        elif source_reader == 'inex':
            return INEXReader(source_path, limit)
        elif source_reader == 'inex_dir':
            return INEXDirectoryReader(source_path)
        elif source_reader == 'living_labs':
            return LivingLabsReader(source_path, limit)
        elif source_reader == 'wapo':
            return TRECWashingtonPostReader(source_path, limit=limit)
        elif source_reader == 'wapo_doc_profile':
            return TRECWashingtonPostReader(
                source_path, features_location=features_location, include_ae_doc_profile=True, limit=limit)
        elif source_reader == 'wapo_dbpedia':
            return TRECWashingtonPostReader(source_path, include_dbpedia=True, limit=limit)
        elif source_reader == 'wapo_doc_profile_dbpedia':
            return TRECWashingtonPostReader(
                source_path, features_location=features_location, include_ae_doc_profile=True, include_dbpedia=True,
                limit=limit)
        elif source_reader == 'csv':
            return CSVReader(source_path)
        # elif source_reader == 'gremlin':
        #     return GremlinReader(source_path)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def __iter__(self):
        return self

    def __next__(self):
        raise ArmyAntException("Reader __next__ not implemented")


class Document(object):
    def __init__(self, doc_id, title=None, text=None, triples=None, metadata=None):
        self.doc_id = doc_id
        self.title = title
        self.text = text
        self.triples = triples
        self.metadata = metadata

    def __repr__(self):
        triples = [] if self.triples is None else [str(triple) for triple in self.triples]
        metadata = [] if self.metadata is None else [str((k, v)) for k, v in self.metadata.items()]

        return (
            '-----------------\n'
            'DOC ID:\n%s\n\n'
            'TITLE:\n%s\n\n'
            'TEXT (%d chars):\n%s\n%s\n\n'
            'TRIPLES (%d):\n%s\n%s\n\n'
            'METADATA:\n%s\n'
            '-----------------\n'
        ) % (
            self.doc_id,
            self.title,
            len(self.text), self.text[0:2000], '[...]' if len(self.text) > 2000 else '',
            len(triples), '\n\n'.join(triples[0:5]),
            '[...]' if len(triples) > 5 else '', '\n'.join(metadata)
        )


class Entity(object):
    def __init__(self, label=None, uri=None):
        if label is None and uri is None:
            self.is_blank = True
        else:
            self.is_blank = False
            self.label = label
            if uri:
                self.uri = uri
            else:
                self.uri = '#%s' % label            

    def __repr__(self):
        if self.is_blank: return "[blank node]"
        return "(%s, %s)" % (self.label, self.uri)


class WikipediaDataReader(Reader):
    def __init__(self, source_path):
        super(WikipediaDataReader, self).__init__(source_path)
        tar = tarfile.open(source_path)
        self.f = tar.extractfile(tar.getmember('wikipedia_datav1.0/wikipedia.train'))

    def to_plain_text(self, html):
        return html_to_text(html)

    def to_wikipedia_entity(self, label):
        return Entity(label, "http://en.wikipedia.org/wiki/%s" % label.replace(" ", "_"))

    def to_triples(self, entity, html):
        soup = BeautifulSoup(html, 'html.parser', parse_only=SoupStrainer('a'))

        triples = []
        for link in soup:
            if link.has_attr('relation'):
                triples.append((
                    self.to_wikipedia_entity(entity),
                    Entity(link['relation']),
                    self.to_wikipedia_entity(link['title'])))

        return triples

    def __next__(self):
        url = None
        entity = None
        html = ''
        for line in self.f:
            line = line.decode('utf-8')
            if line == '\n':
                return Document(
                    doc_id=url,
                    title=entity,
                    text=self.to_plain_text(html),
                    triples=self.to_triples(entity, html),
                    metadata={'url': url, 'name': entity})

            elif line.startswith('url='):
                match = re.search(r'url=(http://[^.]+\.wikipedia\.org/wiki/(.*))', line.strip())
                if match:
                    url = match.group(1)
                    entity = match.group(2).replace('_', ' ')

            else:
                html = html + line

        raise StopIteration


class INEXReader(Reader):
    def __init__(self, source_path, limit=None, title_index=None):
        super(INEXReader, self).__init__(source_path)
        self.limit = limit

        self.counter = 0
        self.parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        self.doc_xpath = '//bdy/descendant-or-self::*[not(ancestor-or-self::template) and not(self::caption)]'
        self.tar = tarfile.open(source_path, 'r|bz2')

        if title_index:
            if type(title_index) is str:
                logger.info("Using provided title index %s for %s" % (title_index, source_path))
                self.title_index = shelve.open(title_index, 'r')
            else:
                logger.info("Using provided title index dictionary for %s" % source_path)
                self.title_index = title_index
        else:
            with tarfile.open(source_path, 'r|bz2') as tar:
                logger.info("Indexing titles in %s by doc_id" % source_path)
                self.title_index = {}
                for member in tar:
                    if not member.name.endswith('.xml'): continue
                    try:
                        article = etree.parse(tar.extractfile(member), self.parser)
                        page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                        title = get_first(article.xpath('//header/title/text()'))
                        self.title_index[page_id] = title
                    except etree.XMLSyntaxError:
                        logger.warning("Error parsing XML, skipping title indexing for %s" % member.name)

    def to_plain_text(self, bdy):
        return re.sub(r'\s+', ' ', ''.join(bdy.xpath('%s/text()' % self.doc_xpath)))

    def to_wikipedia_entity(self, page_id, label):
        #return Entity(label, "http://en.wikipedia.org/?curid=%s" % page_id)
        return Entity(label, "WP%s" % page_id)

    def to_triples(self, page_id, title, bdy):
        triples = []
        for link in bdy.xpath('//link'):
            related_id = get_first(link.xpath('@xlink:href', namespaces={'xlink': 'http://www.w3.org/1999/xlink'}))
            if related_id is None: continue
            related_id = inex.xlink_to_page_id(related_id)

            link_text = get_first(link.xpath('text()'))
            if link_text and len(link_text) < 3: link_text = None

            related_title = self.title_index.get(related_id, link_text)
            if related_title is None: continue
            related_title = related_title.replace('\n', ' ').strip()

            triples.append((
                self.to_wikipedia_entity(page_id, title),
                Entity('related_to'),
                self.to_wikipedia_entity(related_id, related_title)))

        return triples

    def __next__(self):
        url = None

        # Note that this for is only required in case the first element cannot be parsed.
        # If that happens, it skips to the next parsable item.
        while True:
            member = self.tar.next()
            if member is None: break
            if not member.name.endswith('.xml'): continue

            logger.debug("Reading %s" % member.name)

            if self.limit is not None and self.counter >= self.limit: break
            self.counter += 1

            try:
                article = etree.parse(self.tar.extractfile(member), self.parser)
            except etree.XMLSyntaxError:
                logger.warning("Error parsing XML, skipping %s in %s" % (member.name, self.source_path))
                continue

            page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
            title = get_first(article.xpath('//header/title/text()'))

            bdy = get_first(article.xpath('//bdy'))
            if bdy is None: continue

            url = self.to_wikipedia_entity(page_id, title).uri

            return Document(
                doc_id=page_id,
                title=title,
                text=self.to_plain_text(bdy),
                triples=self.to_triples(page_id, title, bdy),
                metadata={'url': url, 'name': title})

        self.tar.close()
        if type(self.title_index) is shelve.DbfilenameShelf: self.title_index.close()
        raise StopIteration


class INEXDirectoryReader(Reader):
    def __init__(self, source_path, use_memory=False):
        super(INEXDirectoryReader, self).__init__(source_path)

        self.use_memory = use_memory

        file_paths = glob.glob(os.path.join(source_path, '*.tar.bz2'))

        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)

        logger.info("Indexing titles by doc_id for all archives in %s" % source_path)

        if use_memory:
            title_index = {}
        else:
            self.tmp_dir = tempfile.mkdtemp()
            logger.info("Using temporary directory %s for %s" % (self.tmp_dir, source_path))

            title_index_path = os.path.join(self.tmp_dir, 'title_index')
            title_index = shelve.open(title_index_path)

        num_docs = 0
        for file_path in file_paths:
            with tarfile.open(file_path, 'r|bz2') as tar:
                for member in tar:
                    if not member.name.endswith('.xml'): continue
                    num_docs += 1
                    try:
                        article = etree.parse(tar.extractfile(member), parser)
                        page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                        title = get_first(article.xpath('//header/title/text()'))
                        title_index[page_id] = title
                    except etree.XMLSyntaxError:
                        logger.warning(
                            "Error parsing XML, skipping title indexing for %s in %s" % (member.name, source_path))

        if type(title_index) is shelve.DbfilenameShelf: title_index.close()

        logger.info(
            "Finished indexing titles by doc_id for %d documents in all archives in %s" % (num_docs, source_path))

        inex_iterators = [
            iter(INEXReader(file_path, title_index=title_index if use_memory else title_index_path))
            for file_path in file_paths
        ]
        self.it = itertools.chain(*inex_iterators)

    def __next__(self):
        try:
            return next(self.it)
        except StopIteration:
            if not self.use_memory:
                logger.info("Removing temporary directory %s for %s" % (self.tmp_dir, self.source_path))
                shutil.rmtree(self.tmp_dir)
            raise


class LivingLabsReader(Reader):
    def __init__(self, source_path, limit=None):
        super(LivingLabsReader, self).__init__(source_path)
        self.limit = limit

        base_url, api_key = source_path.split('::')

        self.base_url = urljoin(base_url, "/api/v2/participant/")
        self.api_key = api_key
        self.headers = {'Content-Type': 'application/json'}
        self.auth = HTTPBasicAuth(api_key, '')

        requests_cache.install_cache('living_labs_cache', expire_after=10800)

        self.docs = self.get_docs()
        self.idx = 0

        if self.limit: self.docs = self.docs[0:self.limit]

    def get_docs(self):
        logging.info("Retrieving Living Labs documents")
        r = requests.get(urljoin(self.base_url, 'docs'), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        return r.json()['docs']

    def format_author_name(self, name):
        if name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                return '%s %s' % (parts[1].strip(), parts[0].strip())
        return name

    def to_text(self, doc, fields=['title'], content_fields=['abstract']):
        text = [doc[field] for field in fields]
        text.extend([doc['content'][field] for field in content_fields])
        return '\n'.join(filter(lambda d: d is not None, text))

    def to_triples(self, doc,
                   content_fields=['author', 'language', 'issued', 'publisher', 'type', 'subject', 'description']):
        triples = []
        for field in content_fields:
            if field in doc['content'] and doc['content'][field]:
                if field == 'author': doc['content'][field] = self.format_author_name(doc['content'][field])
                triples.append((Entity(doc['docid']), Entity(field), Entity(doc['content'][field])))
        return triples

    def __next__(self):
        if self.idx >= len(self.docs):
            raise StopIteration
        else:
            doc = self.docs[self.idx]
            self.idx += 1
            return Document(
                doc_id=doc['docid'],
                text=self.to_text(doc),
                triples=self.to_triples(doc))


class MongoDBReader(Reader):
    def __init__(self, source_path):
        super(MongoDBReader, self).__init__(source_path)

        db_location_parts = re.split(r'[:/]', source_path)

        if len(db_location_parts) >= 3:
            db_host = db_location_parts[0]
            db_port = int(db_location_parts[1])
            db_name = db_location_parts[1]
        elif len(db_location_parts) == 2:
            db_host = db_location_parts[0]
            db_port = 27017
            db_name = db_location_parts[1]
        else:
            db_host = 'localhost'
            db_port = 27017
            db_name = db_location_parts[0]

        try:
            self.client = MongoClient(db_host, db_port)
        except ConnectionFailure:
            raise ArmyAntException("Could not connect to MongoDB instance on %s:%s" % (db_host, db_port))

        self.db = self.client[db_name]


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
        return Entity(author_name, 'https://www.washingtonpost.com/people/%s' % (author_name.lower().replace(' ', '-')))

    def parse_feature_array(self, feature_value, dicretized_version=False):
        if dicretized_version:
            if feature_value == 'null': return []
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
        triples = set([])

        if not self.include_ae_doc_profile and not self.include_dbpedia: return list(triples)

        if self.ac_ner is None:
            self.ac_ner = AhoCorasickEntityExtractor("/opt/army-ant/gazetteers/all.txt")

        triples.add((
            Entity(),
            Entity('has_author'),
            self.to_washington_post_author_entity(doc['author'])
        ))

        doc_id = doc['id']
        text = self.to_plain_text(doc, limit=3)
        entities = self.ac_ner.extract(text)

        # for entity in entities:
        #     triples.add((
        #         Entity(),
        #         Entity(label="mentions"),
        #         Entity(label=entity)
        #     ))

        if self.include_ae_doc_profile:
            doc_features = self.features.loc[doc['id']]
            for feature_name in doc_features.index:
                if feature_name == 'Keywords':
                    # feature_values = sorted(self.parse_feature_array(doc_features[feature_name]), key=lambda kw: kw[1])
                    # feature_values = [k for k, _ in feature_values[0:5]]
                    feature_values = self.parse_feature_array(doc_features[feature_name], dicretized_version=True)
                elif feature_name == 'ReadingComplexity':
                    feature_values = [doc_features[feature_name].split('~', 1)[0]]
                elif feature_name == 'EmotionCategories':
                    # feature_values = sorted(self.parse_feature_array(doc_features[feature_name]), key=lambda kw: kw[1])
                    # feature_values = [k for k, w in feature_values if w >= 0.5]
                    feature_values = self.parse_feature_array(doc_features[feature_name], dicretized_version=True)
                else:
                    feature_values = [doc_features[feature_name]]
                
                if feature_values is None or len(feature_values) == 0: continue

                for feature_value in feature_values:
                    triples.add((
                        Entity(),
                        Entity(label=feature_name),
                        Entity(label=feature_value)
                    ))

        if self.include_dbpedia:
            logger.debug("Fetching DBpedia triples for %d entities in document %s" % (len(entities), doc_id))

            max_retries = 10

            retries_left = max_retries
            retry_wait = 0

            while True:
                try:
                    dbpedia_triples = list(fetch_dbpedia_triples(entities))
                    break
                except:
                    if retries_left > 0:
                        retry_wait += 10 * (max_retries - retries_left + 1)
                        logger.exception(
                            "Error retrieving triples for %d entities in document %s, retrying in %d seconds (%d retries left)" % (
                                len(entities), doc_id, retry_wait, retries_left))
                        retries_left -= 1
                        time.sleep(retry_wait)
                    else:
                        logger.exception("Could not retrieve triples for %d entities in document %s, giving up (returning %d cached triples)" % (
                            len(entities), doc_id, len(triples)))
                        dbpedia_triples = []
                        break

            for (s, sl), (p, pl), (o, ol) in dbpedia_triples:
                triples.add((
                    Entity(sl, s),
                    Entity(pl, p),
                    Entity(ol, o)
                ))

        return list(triples)

    def __next__(self):
        if not self.limit is None and self.counter >= self.limit:
            raise StopIteration

        try:
            doc = next(self.articles)
        except StopIteration:
            self.articles.close()
            doc = next(self.blog_posts)

        if doc:
            logger.debug("Reading %s" % doc['id'])

            text = self.to_plain_text(doc)
            triples = self.build_triples(doc)

            self.counter += 1

            return Document(
                doc_id=doc['id'],
                title=doc['title'],
                text=text,
                triples=triples,
                metadata={'url': doc['article_url'], 'name': doc['title']})

        self.blog_posts.close()
        self.client.close()
        raise StopIteration


class CSVReader(Reader):
    def __init__(self, source_path, doc_id_suffix=':doc_id', text_suffix=':text'):
        super(CSVReader, self).__init__(source_path)

        self.reader = csv.DictReader(open(source_path, newline=''))
        self.doc_id_suffix = doc_id_suffix
        self.text_suffix = text_suffix

        if not any([fieldname.endswith(self.text_suffix) for fieldname in self.reader.fieldnames]):
            raise ArmyAntException(
                "CSV must have at least one column name with a %s suffix (other supported suffixes include %s)" % (
                    self.text_suffix, self.doc_id_suffix))

    def __next__(self):
        for row in self.reader:
            doc_id = None
            text = []

            for k in row.keys():
                if k.endswith(self.text_suffix):
                    text.append(row[k])
                elif k.endswith(self.doc_id_suffix):
                    doc_id = row[k]

            text = '\n'.join(text)

            return Document(doc_id=doc_id, text=text)

        raise StopIteration


if __name__ == '__main__':
    config_logger(logging.DEBUG)

    r = TRECWashingtonPostReader(
        'wapo_sample', features_location='/opt/army-ant/features/wapo-sample', include_ae_doc_profile=True)
    c = 0
    for doc in r:
        print(doc)
        c+=1
        if c % 10 == 0: sys.exit(0)
