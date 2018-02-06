#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# text.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import collections
import logging
import os
import pickle
import string

import langdetect
import nltk
from langdetect.lang_detect_exception import LangDetectException
from nltk import word_tokenize
from nltk.corpus import stopwords, mac_morpho

logger = logging.getLogger(__name__)


def detect_language(text):
    try:
        lang = langdetect.detect(text)
    except LangDetectException:
        lang = 'en'
    return lang


def analyze(text, remove_stopwords=True, remove_punctuation=True):
    tokens = word_tokenize(text.lower())
    try:
        lang = langdetect.detect(text)
    except:
        logger.warning("Could not detect language, using 'en' by default")
        lang = 'en'
    tokens = filter_tokens(tokens, lang=lang, remove_stopwords=remove_stopwords, remove_punctuation=remove_punctuation)
    return tokens


def filter_tokens(tokens, lang, remove_stopwords=True, remove_punctuation=True):
    filtered_tokens = []
    for token in tokens:
        if remove_stopwords:
            if lang == 'pt':
                sw = stopwords.words('portuguese')
            else:
                sw = stopwords.words('english')

            if token in sw: continue

        if remove_punctuation:
            for ch in string.punctuation:
                token = token.replace(ch, '')

        token = token.strip()

        if token == '': continue

        filtered_tokens.append(token)

    return filtered_tokens


def bag_of_words(tokens):
    return collections.Counter(tokens).most_common()


def split_sentences(text):
    lang = detect_language(text)

    if lang == 'pt':
        stokenizer = nltk.data.load('tokenizers/punkt/portuguese.pickle')
    else:
        stokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

    return stokenizer.tokenize(text.strip())


class EnglishPOSTagger(object):
    def tag(self, token):
        return nltk.pos_tag(token)


def simplify_pos_tag(t, delimiter='+'):
    if delimiter in t:
        if delimiter == '-':
            return t[0:t.index(delimiter)]
        return t[t.index(delimiter) + 1:]
    return t


def get_pos_tagger(model_path, lang='pt'):
    if os.path.isfile(model_path):
        logger.info("Loading POS tagger at %s" % model_path)
        with open(model_path, 'rb') as f:
            pos_tagger = pickle.load(f)
    else:
        if lang == 'pt':
            logger.info("Training and saving portuguese POS tagger to %s" % model_path)
            tagged_sentences = mac_morpho.tagged_sents()
            tagged_sentences = [[(w.lower(), t) for (w, t) in s] for s in tagged_sentences if s]
            train = tagged_sentences
            tagger_default = nltk.DefaultTagger('N')
            tagger_unigram = nltk.UnigramTagger(train, backoff=tagger_default)
            pos_tagger = nltk.BigramTagger(train, backoff=tagger_unigram)
            with open(model_path, "wb") as f:
                pickle.dump(pos_tagger, f)
        else:
            logger.info("Using default english POS tagger for '%s'" % lang)
            pos_tagger = EnglishPOSTagger()

    return pos_tagger


def remove_by_pos_tag(pos_tagger, tokens, tags):
    filtered_tokens = []
    tagged_tokens = pos_tagger.tag(tokens)
    for token, tag in tagged_tokens:
        if not tag in tags:
            filtered_tokens.append(token)
    return filtered_tokens
