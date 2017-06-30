#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import tarfile, re, logging, os, requests, requests_cache
from lxml import etree
from io import StringIO
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth
from army_ant.util import html_to_text, get_first
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Reader(object):
    @staticmethod
    def factory(source_path, source_reader, limit=None):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        elif source_reader == 'inex':
            return INEXReader(source_path, limit)
        elif source_reader == 'living_labs':
            return LivingLabsReader(source_path, limit)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def __iter__(self):
        return self

    def __next__(self):
        raise ArmyAntException("Reader __next__ not implemented")

class Document(object):
    def __init__(self, doc_id, text = None, triples = None, metadata = None):
        self.doc_id = doc_id
        self.text = text
        self.triples = triples
        self.metadata = metadata

    def __repr__(self):
        if self.triples is None:
            triples = []
        else:
            triples = '\n'.join([str(triple) for triple in self.triples])

        if self.metadata is None:
            metadata = []
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
                    doc_id = url,
                    text = self.to_plain_text(html),
                    triples = self.to_triples(entity, html),
                    metadata = { 'url': url, 'name': entity })

            elif line.startswith('url='):
                match = re.search(r'url=(http://[^.]+\.wikipedia\.org/wiki/(.*))', line.strip())
                if match:
                    url = match.group(1)
                    entity = match.group(2).replace('_', ' ')

            else:
                html = html + line

        raise StopIteration

class INEXReader(Reader):
    def __init__(self, source_path, limit=None):
        super(INEXReader, self).__init__(source_path)
        self.limit = limit

        self.counter = 0
        self.parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        self.doc_xpath = '//bdy/descendant-or-self::*[not(ancestor-or-self::template) and not(self::caption)]'

        logger.info("Loading members from tar file")
        self.tar = tarfile.open(source_path)
        self.members = self.filter_xml_files(self.tar.getmembers())
        logger.info("Members from tar file loaded")

    def to_plain_text(self, bdy):
        return re.sub(r'\s+', ' ', ''.join(bdy.xpath('%s/text()' % self.doc_xpath)))

    def to_wikipedia_entity(self, page_id, label):
        return Entity(label, "http://en.wikipedia.org/?curid=%s" % page_id)

    def xlink_to_page_id(self, xlink):
        _, filename = os.path.split(xlink)
        return os.path.splitext(filename)[0]

    def to_triples(self, page_id, title, bdy):
        triples = []
        for link in bdy.xpath('//link'):
            related_id = get_first(link.xpath('@xlink:href', namespaces = { 'xlink': 'http://www.w3.org/1999/xlink' }))
            related_title = get_first(link.xpath('text()'))
            
            if related_id is None or related_title is None: continue

            related_id = self.xlink_to_page_id(related_id)
            related_title = related_title.strip()

            triples.append((
                self.to_wikipedia_entity(page_id, title),
                'related_to',
                self.to_wikipedia_entity(related_id, related_title)))

        return triples

    def filter_xml_files(self, members):
        for member in members:
            if os.path.splitext(member.name)[1] == '.xml':
                yield member

    def __next__(self):
        url = None
        entity = None
        html = ''

        for member in self.members:
            logger.debug("Reading %s" % member.name)

            if self.limit is not None and self.counter >= self.limit: break
            self.counter += 1

            try:
                article = etree.parse(self.tar.extractfile(member), self.parser)
            except etree.XMLSyntaxError:
                logger.warn("Error parsing XML, skipping %s" % member.name)
                continue

            page_id = self.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
            title = get_first(article.xpath('//header/title/text()'))

            bdy = get_first(article.xpath('//bdy'))
            if bdy is None: continue

            template = bdy.xpath('//template')

            url = self.to_wikipedia_entity(page_id, title).url

            return Document(
                doc_id = page_id,
                text = self.to_plain_text(bdy),
                triples = self.to_triples(page_id, title, bdy),
                metadata = { 'url': url, 'name': title })

        raise StopIteration

class LivingLabsReader(Reader):
    def __init__(self, source_path, limit=None):
        super(LivingLabsReader, self).__init__(source_path)
        self.limit = limit

        base_url, api_key = source_path.split('::')
        
        self.base_url = urljoin(base_url, "/api/v2/participant/")
        self.api_key = api_key
        self.headers = { 'Content-Type': 'application/json' }
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

    def to_triples(self, doc, content_fields=['author', 'language', 'issued', 'publisher', 'type', 'subject', 'description']):
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
                doc_id = doc['docid'],
                text = self.to_text(doc),
                triples = self.to_triples(doc))
