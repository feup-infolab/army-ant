#!/usr/bin/python
# -*- coding: utf8 -*-
#
# reader.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import tarfile, re
from bs4 import BeautifulSoup, SoupStrainer
from collections import Iterator
from util import html_to_text
from exception import ArmyAntException

class Reader(Iterator):
    @staticmethod
    def factory(source_path, source_reader):
        if source_reader == 'wikipedia_data':
            return WikipediaDataReader(source_path)
        else:
            raise ArmyAntException("Unsupported source reader %s" % source_reader)

    def __init__(self, source_path):
        self.source_path = source_path

    def next(self):
        raise ArmyAntException("Reader not implemented")

class Document(object):
    def __init__(self, text, triples = None):
        self.text = text
        self.triples = triples

    def __str__(self):
        return '-----------------\nTEXT:\n%s\n\nTRIPLES:\n%s\n-----------------\n' % (
            self.text, '\n'.join([str(triple) for triple in self.triples]))

class WikipediaDataReader(Reader):
    def __init__(self, source_path):
        super(WikipediaDataReader, self).__init__(source_path)
        tar = tarfile.open(source_path)
        self.f = tar.extractfile(tar.getmember('wikipedia_datav1.0/wikipedia.train'))

    def to_plain_text(self, html):
        return html_to_text(html)

    def to_triples(self, entity, html):
        soup = BeautifulSoup(html, parseOnlyThese=SoupStrainer('a'))

        triples = []
        for link in soup:
            if link.has_attr('relation'):
                triples.append((entity, link['relation'], link['title']))

        return triples

    def next(self):
        entity = None
        html = ''
        for line in self.f:
            if line == '\n':
                return Document(
                    text = self.to_plain_text(html),
                    triples = self.to_triples(entity, html))

            elif line.startswith('url='):
                match = re.search(r'url=http://en\.wikipedia\.org/wiki/(.*)', line.strip())
                if match:
                    entity = match.group(1).replace('_', ' ')

            else:
                html = html + line

        raise StopIteration
