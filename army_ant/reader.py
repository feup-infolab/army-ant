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
import requests
import requests_cache
import shelve
import shutil
import tarfile
import tempfile
from urllib.parse import urljoin

from bs4 import BeautifulSoup, SoupStrainer
from lxml import etree
from requests.auth import HTTPBasicAuth

from army_ant.exception import ArmyAntException
# from army_ant.index import Index
from army_ant.util import inex, html_to_text, get_first

logger = logging.getLogger(__name__)


class Reader(object):
    @staticmethod
    def factory(source_path, source_reader, limit=None):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        elif source_reader == 'inex':
            return INEXReader(source_path, limit)
        elif source_reader == 'inex_dir':
            return INEXDirectoryReader(source_path)
        elif source_reader == 'living_labs':
            return LivingLabsReader(source_path, limit)
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
    def __init__(self, doc_id, entity=None, text=None, triples=None, metadata=None):
        self.doc_id = doc_id
        self.entity = entity
        self.text = text
        self.triples = triples
        self.metadata = metadata

    def __repr__(self):
        if self.triples is None:
            triples = []
        else:
            triples = '\n'.join([str(triple) for triple in self.triples])

        if self.metadata is None:
            metadata = ''
        else:
            metadata = '\n'.join([str((k, v)) for k, v in self.metadata.items()])

        return '-----------------\nDOC ID:\n%s\n\nTEXT:\n%s\n\nTRIPLES:\n%s\n\nMETADATA:\n%s\n-----------------\n' % (
            self.doc_id, self.text, triples, metadata)


class Entity(object):
    def __init__(self, label, url=None):
        self.label = label
        self.url = url

    def __repr__(self):
        return "(%s, %s)" % (self.label, self.url)


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
                    link['relation'],
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
                    entity=entity,
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
                self.title_index = shelve.open(title_index)
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
                        logger.warn("Error parsing XML, skipping title indexing for %s" % member.name)

    def to_plain_text(self, bdy):
        return re.sub(r'\s+', ' ', ''.join(bdy.xpath('%s/text()' % self.doc_xpath)))

    def to_wikipedia_entity(self, page_id, label):
        return Entity(label, "http://en.wikipedia.org/?curid=%s" % page_id)

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
                'related_to',
                self.to_wikipedia_entity(related_id, related_title)))

        return triples

    def __next__(self):
        url = None
        entity = None
        html = ''

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
                logger.warn("Error parsing XML, skipping %s in %s" % (member.name, self.source_path))
                continue

            page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
            title = get_first(article.xpath('//header/title/text()'))

            bdy = get_first(article.xpath('//bdy'))
            if bdy is None: continue

            template = bdy.xpath('//template')

            url = self.to_wikipedia_entity(page_id, title).url

            return Document(
                doc_id=page_id,
                entity=title,
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
                        logger.warn(
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
                triples.append((Entity(doc['docid']), field, Entity(doc['content'][field])))
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

    # TODO should this be here? should we use a NullReader read the graph some other way?
    # class GremlinReader(Reader):
    # def __init__(self, source_path):
    # super(GremlinReader, self).__init__(source_path)

    # loop = asyncio.get_event_loop()
    # self.index = Index.open(source_path, 'gremlin', loop)
    # self.edge_list = self.index.to_edge_list(use_names=True)

    # def __next__(self):
    # for edge in self.edge_list:
    # doc_id = None
    # text = []

    # for k in row.keys():
    # if k.endswith(self.text_suffix):
    # text.append(row[k])
    # elif k.endswith(self.doc_id_suffix):
    # doc_id = row[k]

    # text = '\n'.join(text)

    # return Document(doc_id = doc_id, text = text)

    # raise StopIteration
