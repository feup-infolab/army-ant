#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# text.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import string, collections
from nltk import word_tokenize
from nltk.corpus import stopwords

def analyze(text, remove_stopwords=True):
    tokens = word_tokenize(text.lower())
    if remove_stopwords:
        tokens = [token for token in tokens if token not in stopwords.words('english') and not token[0] in string.punctuation]
    return tokens

def bag_of_words(tokens):
    return collections.Counter(tokens).most_common()
