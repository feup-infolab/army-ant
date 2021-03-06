#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# aho_corasick_entity_extractor.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-05-30
import logging
import os
import sys
import ahocorasick
import pickle

logger = logging.getLogger(__name__)


class AhoCorasickEntityExtractor():
    def __init__(self, list_path=None, pickle_path=None):
        assert list_path is not None or pickle_path is not None, "At least one of list_path and pickle_path must be set"

        if list_path and pickle_path is None or not os.path.exists(pickle_path):
            logger.info("Building Aho-Corasick finite state machine based on %s" % list_path)
            self.automaton = ahocorasick.Automaton()

            with open(list_path, 'r') as f:
                for line in f:
                    entity = line.strip().lower()
                    self.automaton.add_word(entity, (0, entity))

            self.automaton.make_automaton()

            if pickle_path:
                logger.info("Saving Aho-Corasick finite state machine to %s" % pickle_path)
                with open(pickle_path, 'wb') as f:
                    pickle.dump(self.automaton, f)
        else:
            logger.info("Loading Aho-Corasick finite state machine from %s" % pickle_path)
            with open(pickle_path, 'rb') as f:
                self.automaton = pickle.load(f)

    def extract(self, text):
        entities = set([])

        for end_index, (insert_order, original_value) in self.automaton.iter(text):
            start_index = end_index - len(original_value) + 1
            if (start_index != 0 and str.isalnum(text[start_index - 1])
                    or end_index + 1 != len(text) and str.isalnum(text[end_index + 1])): continue

            entities.add(text[start_index:end_index + 1])

            # print((start_index, end_index, (insert_order, original_value)))
            # assert text[start_index:start_index + len(original_value)] == original_value

        return list(entities)