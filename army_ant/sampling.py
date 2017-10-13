#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# features.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import logging, os, random, glob, tarfile, bz2
from lxml import etree
from army_ant.util import inex, get_first
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class INEXSampler(object):
    def __init__(self, qrels_input_path, qrels_output_path, topics_input_path, topics_output_path,
                 corpus_input_path, corpus_output_path, include_linked=False, query_sample_size=None):
        self.qrels_input_path = qrels_input_path
        self.qrels_output_path = qrels_output_path
        self.topics_input_path = topics_input_path
        self.topics_output_path = topics_output_path
        self.corpus_input_path = corpus_input_path
        self.corpus_output_path = corpus_output_path
        self.query_sample_size = query_sample_size

        if os.path.exists(self.corpus_output_path):
            raise ArmyAntException("%s already exists" % self.corpus_output_path)

        qrels_dir = os.path.dirname(self.qrels_output_path)
        if os.path.exists(qrels_dir):
            raise ArmyAntException("%s already exists" % qrels_dir)

        topics_dir = os.path.dirname(self.topics_output_path)
        if os.path.exists(topics_dir):
            raise ArmyAntException("%s already exists" % topics_dir)

        os.makedirs(self.corpus_output_path)
        os.makedirs(qrels_dir)
        os.makedirs(topics_dir)

    def qids_sample(self):
        with open(self.qrels_input_path, 'r') as f_qrels:
            qids = set([line.split(' ')[0] for line in f_qrels])

            if self.query_sample_size:
                query_sample_size = min(len(qids), self.query_sample_size)
                if query_sample_size == len(qids):
                    logger.info("Using all %d queries" % len(qids))
                else:
                    logger.info("Sampling %d random queries" % query_sample_size)
            else:
                query_sample_size = len(qids)
                logger.info("Using all %d queries" % len(qids))

            qids_sample = random.sample(qids, query_sample_size)

            return qids_sample

    def get_doc_ids(self, qids):
        doc_ids = set([])
        with open(self.qrels_input_path, 'r') as f_qrels:
            for line in f_qrels:
                cols = line.split(' ')
                qid = cols[0]
                if qid in qids:
                    doc_ids.add(cols[2])
        return doc_ids

    def create_qrels(self, qids):
        logger.info("Writing %s" % self.qrels_output_path)
        with open(self.qrels_input_path, 'r') as f_qrels, open(self.qrels_output_path, 'w') as f:
            for line in f_qrels:
                cols = line.split(' ')
                qid = cols[0]
                if qid in qids:
                    f.write(line)

    def create_topics(self, qids):
        logger.info("Writing %s" % self.topics_output_path)
        with open(self.topics_input_path, 'r') as f_topics:
            topics = etree.parse(f_topics)
            for topic in topics.xpath('//topic[%s]' % ' and '.join(map(lambda qid: "@id != '%s'" % qid, qids))):
                topic.getparent().remove(topic)
            topics.write(self.topics_output_path)

    def create_subset(self, doc_ids_sample, append=False, compress=False):
        file_paths = glob.glob(os.path.join(self.corpus_input_path, '*.tar.bz2'))
        out_file_paths = []

        for file_path in file_paths:
            out_file_path = os.path.join(self.corpus_output_path, os.path.basename(file_path))
            out_file_paths.append(out_file_path)

            if append:
                logger.info("Appending to %s" % out_file_path)
                mode = 'a'
            else:
                logger.info("Writing %s" % out_file_path)
                mode = 'w'

            with tarfile.open(file_path, 'r|bz2') as in_tar, tarfile.open(out_file_path, mode) as out_tar:
                for member in in_tar:
                    if member.name.endswith('.xml'):
                        page_id = inex.xlink_to_page_id(member.name)
                        if page_id in doc_ids_sample:
                            out_tar.addfile(member, in_tar.extractfile(member))

            if compress:
                logger.info("Compressing %s tar with bzip2" % out_file_path)
                with open(out_file_path, 'rb') as f:
                    compressed_data = bz2.compress(f.read())
                with open(out_file_path, 'wb') as f:
                    f.write(compressed_data)

        return out_file_paths

    def get_linked_doc_ids(self, file_paths, source_docs_ids):
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)

        target_doc_ids = set([])
        for file_path in file_paths:
            with tarfile.open(file_path, 'r') as in_tar:
                for member in in_tar:
                    if member.name.endswith('.xml'):
                        article = etree.parse(in_tar.extractfile(member), parser)
                        bdy = get_first(article.xpath('//bdy'))
                        if bdy is None: continue
                        for link in bdy.xpath('//link'):
                            target_doc_id = get_first(link.xpath('@xlink:href', namespaces = { 'xlink': 'http://www.w3.org/1999/xlink' }))
                            if target_doc_id is None: continue
                            target_doc_id = inex.xlink_to_page_id(target_doc_id)
                            target_doc_ids.add(target_doc_id)

        return target_doc_ids.difference(source_docs_ids)

    def sample(self):
        qids_sample = self.qids_sample()
        doc_ids_sample = self.get_doc_ids(qids_sample)

        logger.info("Creating sample based on %d documents" % len(doc_ids_sample))
        self.create_qrels(qids_sample)
        self.create_topics(qids_sample)
        sample_file_paths = self.create_subset(doc_ids_sample)

        doc_ids_linked = self.get_linked_doc_ids(sample_file_paths, doc_ids_sample)
        logger.info("Expanding sample with %d linked documents" % len(doc_ids_linked))
        self.create_subset(doc_ids_linked, append=True, compress=True)
