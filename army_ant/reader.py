#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import tarfile, re
from bs4 import BeautifulSoup, SoupStrainer
from army_ant.util import html_to_text
from army_ant.exception import ArmyAntException

class Reader(object):
    @staticmethod
    def factory(source_path, source_reader):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def __iter__(self):
        return self

    def __next__(self):
        raise ArmyAntException("Reader __next__ not implemented")

class Document(object):
    def __init__(self, doc_id, text, triples = None):
        self.doc_id = doc_id
        self.text = text
        self.triples = triples

    def __str__(self):
        return '-----------------\nDOC ID:\n%s\n\nTEXT:\n%s\n\nTRIPLES:\n%s\n-----------------\n' % (
            self.doc_id, self.text, '\n'.join([str(triple) for triple in self.triples]))

class WikipediaDataReader(Reader):
    def __init__(self, source_path):
        super(WikipediaDataReader, self).__init__(source_path)
        tar = tarfile.open(source_path)
        self.f = tar.extractfile(tar.getmember('wikipedia_datav1.0/wikipedia.train'))

    def to_plain_text(self, html):
        return html_to_text(html)

    def to_triples(self, entity, html):
        soup = BeautifulSoup(html, 'html.parser', parse_only=SoupStrainer('a'))

        triples = []
        for link in soup:
            if link.has_attr('relation'):
                triples.append((entity, link['relation'], link['title']))

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
                    triples = self.to_triples(entity, html))

            elif line.startswith('url='):
                match = re.search(r'url=(http://[^.]+\.wikipedia\.org/wiki/(.*))', line.strip())
                if match:
                    url = match.group(1)
                    entity = match.group(2).replace('_', ' ')

            else:
                html = html + line

        raise StopIteration
