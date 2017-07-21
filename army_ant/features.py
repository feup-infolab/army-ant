#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# features.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import logging, os, langdetect, string
import networkx as nx
from nltk import word_tokenize
from gensim.models import Word2Vec
from army_ant.text import analyze, split_sentences, get_pos_tagger, remove_by_pos_tag, filter_tokens
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class FeatureExtractor(object):
    @staticmethod
    def factory(method, reader, output_location):
        if method == 'word2vec_simnet':
            return Word2VecSimilarityNetwork(reader, output_location)
        else:
            raise ArmyAntException("Unsupported method %s" % method)

    def __init__(self, reader, output_location):
        self.reader = reader
        self.output_location = output_location

    def extract(self):
        raise ArmyAntException("Extract not implemented for %s" % self.__class__.__name__)

class Word2VecSimilarityNetwork(FeatureExtractor):
    def __init__(self, reader, output_location):
        super().__init__(reader, output_location)

        if not os.path.exists(output_location):
            os.mkdir(output_location)

        self.model_path = os.path.join(output_location, 'word2vec.model')
        self.graph_path = os.path.join(output_location, 'word2vec_simnet.graphml')
        self.pos_tagger_model_path_basename = os.path.join(output_location, 'pos_tagger')

    def build_sentence_dataset(self):
        logging.info("Extracting sentences from documents")
        self.sentences = []
        pos_taggers = {}
        #filter_tags = { 'pt': ['v-inf', 'v-fin', 'v-pcp', 'prp', 'adv', 'art', 'conj-s', 'conj-c'], 'en': ['VB', 'VBP'] }
        filter_tags = { 'pt': ['V', 'PCP', 'VAUX', 'PREP', 'CUR', 'NUM', 'PREP|+', 'NPROP', 'PROPESS', 'ART', 'KS', 'ADV'], 'en': ['VB', 'VBP'] }
        for doc in self.reader:
            lang = langdetect.detect(doc.text)
            if not lang in pos_taggers:
                pos_taggers[lang] = get_pos_tagger('%s-%s.pickle' % (self.pos_tagger_model_path_basename, lang), lang)

            for sentence in split_sentences(doc.text):
                tokens = remove_by_pos_tag(pos_taggers[lang], word_tokenize(sentence), tags=filter_tags.get(lang, filter_tags['en']))
                self.sentences.append([token.lower() for token in filter_tokens(tokens, lang)])
        return self.sentences

    def train(self):
        logging.info("Training word2vec model")
        self.model = Word2Vec(self.sentences, size=100, window=5, min_count=2, workers=4)
        self.model.save(self.model_path)
        logging.info("Saved model to %s" % self.model_path)

    def build_similarity_network(self, threshold=0.5):
        logging.info("Building similarity network")
        g = nx.Graph()
        for word in self.model.wv.vocab:
            sim_words = self.model.wv.most_similar(positive=[word], topn=2)
            for (sim_word, weight) in sim_words:
                if weight <= threshold: continue
                g.add_edge(word, sim_word)
        nx.write_graphml(g, self.graph_path)
        logger.info("Saved similarity network to %s" % self.graph_path)

    def extract(self):
        if os.path.exists(self.model_path):
            logging.info("Loading existing word2vec model")
            self.model = Word2Vec.load(self.model_path)
        else:
            self.build_sentence_dataset()
            self.train()

        self.build_similarity_network()
