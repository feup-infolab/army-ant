#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# features.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import logging
import os
from collections import OrderedDict

import igraph
import langdetect
from gensim.models import Word2Vec
from langdetect.lang_detect_exception import LangDetectException
from nltk.stem import SnowballStemmer

from army_ant.exception import ArmyAntException
from army_ant.util.text import (SLOT_PREFIX, filter_tokens, get_pos_tagger,
                                normalize_text, slot_money, slot_numbers,
                                slot_time, slot_urls, split_sentences,
                                tokenize)

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
        self.graph_path = os.path.join(output_location, 'word2vec_simnet.graphml.gz')
        self.pos_tagger_model_path_basename = os.path.join(output_location, 'pos_tagger')

    def preprocess(self, text):
        text = normalize_text(text)
        text = slot_urls(text)
        text = slot_time(text)
        text = slot_money(text)
        text = slot_numbers(text)
        return text

    def build_sentence_dataset(self):
        logging.info("Extracting sentences from documents")

        stemmer = SnowballStemmer('english')

        self.sentences = []
        self.vocabulary = set([])
        pos_taggers = {}

        # Tags to remove: parts-of-speech, such as verbs, result a similarity network that is too dense.
        # filter_tags = {
        #     'pt': ['V', 'PCP', 'VAUX', 'PREP', 'CUR', 'NUM', 'PREP|+', 'NPROP', 'PROPESS', 'ART', 'KS', 'ADV'],
        #     'en': ['VB', 'VBP']
        # }

        doc_count = 0
        for doc in self.reader:
            text = self.preprocess(doc.text)

            try:
                lang = langdetect.detect(text)
            except LangDetectException:
                lang = 'en'

            if lang not in pos_taggers:
                pos_taggers[lang] = get_pos_tagger('%s-%s.pickle' % (self.pos_tagger_model_path_basename, lang), lang)

            for sentence in split_sentences(text):
                # Removing verbs has low impact on vocabularity size.
                # tokens = remove_by_pos_tag(
                #     pos_taggers[lang], tokenize(sentence),
                #     tags=filter_tags.get(lang, filter_tags['en']))
                tokens = tokenize(sentence)

                tokenized_sentence = []

                # Remove stopwords based on lang.
                for token in filter_tokens(tokens, lang):
                    if not token.startswith(SLOT_PREFIX):
                        token = token.lower()

                    if len(token) < 3:
                        continue

                    # Stemming has a higher impact on vocabulary size.
                    token = stemmer.stem(token)

                    tokenized_sentence.append(token)
                    self.vocabulary.add(token)

                self.sentences.append(tokenized_sentence)

            doc_count += 1
            if doc_count % 100 == 0:
                logger.info("%d documents preprocessed" % doc_count)

        logger.info("Finished preprocessing %d documents" % doc_count)
        logger.info("Vocabulary has size %d" % len(self.vocabulary))

        return self.sentences

    def train(self, size=100, window=5, min_count=2, max_vocab_size=None):
        """
        :param size: vector of length `size`, per word.
        :param window: the number of words that form a "context".
        :param min_count: words that appear less than `min_count` times will be ignored.
        :param max_vocab_size: maximum vocabulary size (less frequent words will be removed).
        """
        logging.info("Training word2vec model")
        self.model = Word2Vec(self.sentences, size=size, window=window, min_count=min_count,
                              max_vocab_size=max_vocab_size, workers=4)
        self.model.save(self.model_path)
        logging.info("Saved model to %s" % self.model_path)

    def build_similarity_network(self, k=2, threshold=0.5):
        """
        Builds a similarity network based on embedding similarity, using `k` nearest neighbors to
        establish adjacencies.

        :param k: number of nearest neighbors per word.
        :param threshold: minimum similarity to include the edge.
        """
        logging.info("Building similarity network")

        graph = OrderedDict()

        for word in self.model.wv.vocab:
            sim_words = self.model.wv.most_similar(positive=[word], topn=k)
            for (sim_word, weight) in sim_words:
                if weight <= threshold:
                    continue

                if word not in graph:
                    graph[word] = OrderedDict()

                graph[word][sim_word] = weight

        g = igraph.Graph(directed=False)
        g.add_vertices(iter(graph.keys()))
        edges = [(source, target) for source in graph.keys() for target in graph[source].keys()]
        g.add_edges(edges)
        g.es['weight'] = [weight for source in graph.keys() for weight in graph[source].values()]

        g.write(self.graph_path, format='graphmlz')
        logger.info("Saved similarity network to %s" % self.graph_path)

    def extract(self):
        if os.path.exists(self.model_path):
            logging.info("Loading existing word2vec model")
            self.model = Word2Vec.load(self.model_path)
        else:
            self.build_sentence_dataset()
            self.train()

        self.build_similarity_network()
