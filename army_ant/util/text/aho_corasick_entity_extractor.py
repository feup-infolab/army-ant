#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# aho_corasick_entity_extractor.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-05-30
import logging
import sys
import ahocorasick

from army_ant.setup import config_logger

logger = logging.getLogger(__name__)

class AhoCorasickEntityExtractor():
    def __init__(self, list_path):
        logger.info("Building Aho-Corasick finite state machine based on %s" % list_path)
        self.automaton = ahocorasick.Automaton()

        with open(list_path, 'r') as f:
            for line in f:
                entity = line.strip()
                self.automaton.add_word(entity, (0, entity))

        self.automaton.make_automaton()

    def extract(self, text):
        entities = set([])

        for end_index, (insert_order, original_value) in self.automaton.iter(text):
            start_index = end_index - len(original_value) + 1
            if (start_index != 0 and str.isalnum(text[start_index-1])
                    or end_index + 1 != len(text) and str.isalnum(text[end_index+1])): continue

            entities.add(text[start_index:end_index+1])

            #print((start_index, end_index, (insert_order, original_value)))
            #assert text[start_index:start_index + len(original_value)] == original_value

        return list(entities)


if __name__ == '__main__':
    config_logger()

    if len(sys.argv) < 2:
        print("Usage: %s LIST_PATH" % sys.argv[0])
        sys.exit(1)

    a = AhoCorasickEntityExtractor(sys.argv[1])
    entities = a.extract("Barack Obama was the first president of the United States of America"
                         " and Emma Sipos is an unknown person. And Running.")
    for entity in entities:
        print(entity)
