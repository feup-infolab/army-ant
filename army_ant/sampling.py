#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# features.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import logging, os, random, glob, tarfile
from lxml import etree
from army_ant.util import inex, get_first
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class INEXSampler(object):
    def __init__(self, qrels_input_path, qrels_output_path, corpus_input_path, corpus_output_path, query_sample_size=None):
        self.qrels_input_path = qrels_input_path
        self.qrels_output_path = qrels_output_path
        self.corpus_input_path = corpus_input_path
        self.corpus_output_path = corpus_output_path
        self.query_sample_size = query_sample_size

        #if not os.path.exists(output_location):
            #os.mkdir(output_location)

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

    def create_subset(self, doc_ids_sample):
        file_paths = glob.glob(os.path.join(self.corpus_input_path, '*.tar.bz2'))
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)

        for file_path in file_paths:
            out_file_path = os.path.join(self.corpus_output_path, os.path.basename(file_path))
            logger.info("Writing %s" % out_file_path)
            with tarfile.open(file_path) as in_tar, tarfile.open(out_file_path, 'w') as out_tar:
                members = inex.filter_xml_files(in_tar.getmembers())
                for member in members:
                    try:
                        f_member = in_tar.extractfile(member)
                        article = etree.parse(f_member, parser)
                        page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                        if page_id in doc_ids_sample:
                            out_tar.addfile(in_tar.tarinfo, f_member)
                    except etree.XMLSyntaxError:
                        logger.warn("Error parsing XML, skipping title indexing for %s" % member.name)

    def sample(self):
        qids_sample = self.qids_sample()
        doc_ids_sample = self.get_doc_ids(qids_sample)

        logger.info("Creating sample based on %d documents" % len(doc_ids_sample))
        self.create_qrels(qids_sample)
        self.create_subset(doc_ids_sample)
