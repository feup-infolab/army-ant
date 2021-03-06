#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# count_entities.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-07-23
#
# You can also verify the total entities based on the following command:
#
# awk '{ print $4 }' ~/Data/CoNLL-2003/eng.train \
#   | uniq \
#   | grep -v -E "^O\$" \
#   | grep -v -E "^\$" \
#   | grep -E "I-PER|I-ORG|I-LOC|I-MISC" \
#   | wc -l

import sys
import numpy as np

if len(sys.argv) < 2:
    print("Usage: %s CONLL_DATASET" % sys.argv[0])
    sys.exit(1)

filename = sys.argv[1]

with open(filename, 'r') as fp:
    entities_per_doc = []
    entities_per_sent = []

    doc_entities = None
    sent_entities = None
    prev_tag = None
    curr_tag = None

    for line in fp:
        line = line.strip()
        #print(line, end=" ")

        if line == '-DOCSTART- -X- O O':
            #print("=> DOCSTART")
            if doc_entities is not None:
                entities_per_doc.append(doc_entities)
            doc_entities = 0
            curr_tag = None
        elif line == '':
            #print("=> SENTSTART")
            if sent_entities is not None:
                entities_per_sent.append(sent_entities)
            sent_entities = 0
            curr_tag = None
        else:
            curr_tag = line.split()[3]
            #print("=> TAG: %s" % curr_tag, end=" ")

        if prev_tag in set(['I-PER', 'I-ORG', 'I-LOC', 'I-MISC']) and curr_tag != prev_tag:
            #print("=> COUNT ENTITY")
            doc_entities += 1
            sent_entities += 1
        else:
            #print()
            pass

        prev_tag = curr_tag

    if doc_entities is not None:
        entities_per_doc.append(doc_entities)

    if doc_entities is not None:
        entities_per_doc.append(sent_entities)

    print("Avg. ent. p/doc.\t", np.mean(entities_per_doc))
    print("Avg. ent. p/sent.\t", np.mean(entities_per_sent))

    print("Tot. ent. p/doc.\t", np.sum(entities_per_doc))
    print("Tot. ent. p/sent.\t", np.sum(entities_per_sent))

    print(
        "Num. docs w/entities\t", np.count_nonzero(entities_per_doc),
        "\t(%.2f%%)" % (np.count_nonzero(entities_per_doc) / len(entities_per_doc) * 100))
    print(
        "Num. sents w/entities\t", np.count_nonzero(entities_per_sent),
        "\t(%.2f%%)" % (np.count_nonzero(entities_per_sent) / len(entities_per_sent) * 100))
