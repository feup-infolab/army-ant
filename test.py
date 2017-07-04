#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# test.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-15

import logging, asyncio, sys

from army_ant.reader import INEXReader, LivingLabsReader
from army_ant.evaluation import Evaluator, LivingLabsEvaluator

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

def test_inexreader():
    for item in INEXReader("/media/backups/Datasets/INEX 2009/dataset/sample.tar.bz2"):
        print(item)

def test_inexevaluator():
    e = Evaluator.factory(
        "/opt/army-ant/eval/spool/eval_topics_wjrfrryw",
        "/opt/army-ant/eval/spool/eval_assessments_9n0llhsf", 
        "localhost:8184",
        "gow",
        "/opt/army-ant/eval",
        "inex")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(e.run())

def test_livinglabsreader(*argv):
    if len(argv) < 2:
        print("Must provide api_key argument")
        return

    api_key = argv[1]

    c = 0
    for item in LivingLabsReader("http://api.trec-open-search.org::%s" % api_key):
        print(item)
        c += 1
    logging.info("%d items read" % c)

def test_livinglabsevaluator(*argv):
    if len(argv) < 5:
        print("Must provide arguments: index_location, index_type, api_key, run_id")
        return

    index_location = argv[1]
    index_type = argv[2]
    api_key = argv[3]
    run_id = argv[4]
    
    e = LivingLabsEvaluator(index_location, index_type, 'http://api.trec-open-search.org', api_key)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(e.run(run_id))

if __name__ == '__main__':
    # This is used during development to test individual methods.
    #test_inexreader()
    #test_inexevaluator()
    #test_livinglabsreader(*sys.argv)
    test_livinglabsevaluator(*sys.argv)
