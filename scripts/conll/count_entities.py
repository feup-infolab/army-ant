#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# count_entities.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-07-23

import sys
import numpy as np

if len(sys.argv) < 2:
    print("Usage: %s CONLL_DATASET" % sys.argv[0])
    sys.exit(1)

filename=sys.argv[1]

with open(filename, 'r') as fp:
    entities_per_doc = []
    entities_per_sent = []

    doc_entities = None
    sent_entities = None
    prev_tag = None
    curr_tag = None

    for line in fp:
        line = line.strip()

        if line == '-DOCSTART- -X- O O':
            if doc_entities:
                entities_per_doc.append(doc_entities)
                doc_entities = 0
            curr_tag = None
        elif line == '':
            if sent_entities:
                entities_per_sent.append(sent_entities)
                sent_entities = 0
            curr_tag = None
        elif 'I-PER' in line or 'I-ORG' in line or 'I-LOC' in line or 'I-MISC' in line:
            curr_tag = line.split()[3]
            if prev_tag is None:
                prev_tag = curr_tag
        elif prev_tag != curr_tag:
            prev_tag = curr_tag
            if doc_entities:
                doc_entities += 1
            else:
                doc_entities = 1

            if sent_entities:
                sent_entities += 1
            else:
                sent_entities = 1

    print("Avg. entites per doc.\t", np.mean(entities_per_doc))
    print("Avg. entities per sent.\t", np.mean(entities_per_sent))

    print("Tot. entites per doc.\t", np.sum(entities_per_doc))
    print("Tot. entities per sent.\t", np.sum(entities_per_sent))

    print("Number of docs w/entities\t", np.count_nonzero(entities_per_sent))
    print("Number of sents w/entities\t", np.count_nonzero(entities_per_sent))
