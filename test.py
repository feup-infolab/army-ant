#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# test.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-15

import logging, asyncio

from army_ant.reader import INEXReader
from army_ant.evaluation import Evaluator

logging.basicConfig(
    format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

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

if __name__ == '__main__':
    # This is used during development to test individual methods.
    #test_inexreader()
    test_inexevaluator()
