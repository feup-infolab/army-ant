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
import re
import string

import langdetect
import nltk
from langdetect.lang_detect_exception import LangDetectException
from nltk.corpus import stopwords, mac_morpho
from nltk.tokenize import WordPunctTokenizer
from unidecode import unidecode

logger = logging.getLogger(__name__)

SLOT_PREFIX = 'SLOT_'

url_regex = re.compile(r'http[s]?://[^\s]+')
num_regex = re.compile(r'\d+')
time_regex = re.compile(r'(\d{1,2}:\d{2}(:\d{2})?)|(\d{1,2}h(\d{2}(m|(m\d{1,2}s))?)?)|(\d{1,2}(pm|am|PM|AM))')

tokenizer = WordPunctTokenizer()


def normalize_text(text):
    return unidecode(text)


def slot_urls(text, prefix=SLOT_PREFIX):
    return url_regex.sub('%sURL' % prefix, text)


def slot_time(text, prefix=SLOT_PREFIX):
    return time_regex.sub('%sTIME' % prefix, text)


def slot_numbers(text, prefix=SLOT_PREFIX):
    return num_regex.sub(' %sNUM ' % prefix, text)


def detect_language(text):
    try:
        lang = langdetect.detect(text)
    except LangDetectException:
        lang = 'en'
    return lang


def tokenize(text):
    return tokenizer.tokenize(text)


def analyze(text, remove_stopwords=True, remove_punctuation=True):
    tokens = tokenize(text.lower())
    try:
        lang = langdetect.detect(text)
    except:
        logger.warning("Could not detect language, using 'en' by default")
        lang = 'en'
    tokens = filter_tokens(tokens, lang=lang, remove_stopwords=remove_stopwords, remove_punctuation=remove_punctuation)
    return tokens


def filter_tokens(tokens, lang, remove_stopwords=True, remove_punctuation=True, skip_slots=True):
    filtered_tokens = []
    for token in tokens:
        if remove_stopwords:
            if lang == 'pt':
                sw = stopwords.words('portuguese')
            else:
                sw = stopwords.words('english')

            if token in sw: continue

        if remove_punctuation:
            if skip_slots and token.startswith(SLOT_PREFIX): continue
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
            tagged_sentences = [[(w, t) for (w, t) in s] for s in tagged_sentences if s]
            train = tagged_sentences
            tagger_default = nltk.DefaultTagger('N')
            tagger_unigram = nltk.UnigramTagger(train, backoff=tagger_default)
            pos_tagger = nltk.BigramTagger(train, backoff=tagger_unigram)
            with open(model_path, "wb") as f:
                pickle.dump(pos_tagger, f)
        else:
            logger.warning("Using default english POS tagger for '%s'" % lang)
            pos_tagger = EnglishPOSTagger()

    return pos_tagger


def remove_by_pos_tag(pos_tagger, tokens, tags):
    filtered_tokens = []
    tagged_tokens = pos_tagger.tag(tokens)
    for token, tag in tagged_tokens:
        if not tag in tags:
            filtered_tokens.append(token)
    return filtered_tokens
