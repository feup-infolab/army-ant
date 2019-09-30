#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# text.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import collections
import itertools
import logging
import os
import pickle
import re
import string
from collections import OrderedDict

import igraph
import langdetect
import nltk
import yaml
from langdetect.lang_detect_exception import LangDetectException
from nltk.corpus import mac_morpho, stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import WordPunctTokenizer
from unidecode import unidecode

logger = logging.getLogger(__name__)

SLOT_PREFIX = 'SLOT'

url_regex = re.compile(r'http[s]?://[^\s]+')
time_regex = re.compile(r'(\d{1,2}:\d{2}(:\d{2})?)|(\d{1,2}h(\d{2}(m|(m\d{1,2}s))?)?)|(\d{1,2}(pm|am|PM|AM))')
money_regex = re.compile(r'([$€£]\d*\.?\d+)|(\d*\.\d+[$€£])')
num_regex = re.compile(r'\d*\.\d+')

tokenizer = WordPunctTokenizer()


def normalize_text(text):
    return unidecode(text)


def slot_urls(text, prefix=SLOT_PREFIX):
    return url_regex.sub('%s_URL' % prefix, text)


def slot_time(text, prefix=SLOT_PREFIX):
    return time_regex.sub('%s_TIME' % prefix, text)


def slot_money(text, prefix=SLOT_PREFIX):
    return money_regex.sub('%s_MONEY' % prefix, text)


def slot_numbers(text, prefix=SLOT_PREFIX):
    return num_regex.sub('%s_NUM' % prefix, text)


def detect_language(text):
    try:
        lang = langdetect.detect(text)
    except LangDetectException:
        lang = 'en'
    return lang


def tokenize(text):
    return tokenizer.tokenize(text)


def analyze(text, remove_stopwords=True, remove_punctuation=True, stemming=True):
    tokens = tokenize(text.lower())
    # try:
    #     lang = langdetect.detect(text)
    # except:
    #     logger.warning("Could not detect language, using 'en' by default")
    #     lang = 'en'
    lang = "en"
    tokens = filter_tokens(
        tokens, lang=lang, remove_stopwords=remove_stopwords,
        remove_punctuation=remove_punctuation, stemming=stemming)
    return tokens


def filter_tokens(tokens, lang, remove_stopwords=True, remove_punctuation=True, stemming=True, skip_slots=True):
    filtered_tokens = []

    if lang == 'pt':
        sw = stopwords.words('portuguese')
    else:
        sw = stopwords.words('english')

    stemmer = PorterStemmer()

    for token in tokens:
        if remove_stopwords:
            if token in sw:
                continue

        if remove_punctuation:
            if skip_slots and token.startswith(SLOT_PREFIX):
                continue

            for ch in string.punctuation:
                token = token.replace(ch, '')

        token = token.strip()

        if token == '':
            continue

        if stemming:
            token = stemmer.stem(token)

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


# TODO integrate into filter_tokens
def remove_by_pos_tag(pos_tagger, tokens, tags):
    filtered_tokens = []
    tagged_tokens = pos_tagger.tag(tokens)
    for token, tag in tagged_tokens:
        if tag not in tags:
            filtered_tokens.append(token)
    return filtered_tokens


def extract_entities_per_sentence(text, lib='NLTK'):
    assert lib in ('NLTK', 'StanfordNER'), "The valye of 'lib' must either be 'NLTK' or 'StanfordNER'."

    entities = []

    if lib == 'NLTK':
        for sent in nltk.sent_tokenize(text):
            entities_per_sentence = collections.defaultdict(int)
            for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sent))):
                if hasattr(chunk, 'label'):
                    entities_per_sentence[(chunk.label(), ' '.join(c[0] for c in chunk))] += 1
            entities.append(entities_per_sentence)

    elif lib == 'StanfordNER':
        config = yaml.load(open('config.yaml'))
        stanford_ner_location = config.get('defaults', {}).get('depend', {}).get('stanford-ner')

        assert stanford_ner_location, "Please provide the location to the StanfordNER 2015-12-09 directory in the" \
                                      " defaults->depend->stanford-ner configuration section."

        tokenized_sents = []
        for sent in nltk.sent_tokenize(text):
            tokenized_sents.append([
                token.replace('/', '-')
                for token in nltk.word_tokenize(sent)])

        stanford_tagger = nltk.StanfordNERTagger(
            model_filename=os.path.join(stanford_ner_location, 'classifiers/english.all.3class.distsim.crf.ser.gz'),
            path_to_jar=os.path.join(stanford_ner_location, 'stanford-ner-3.6.0.jar'),
            encoding='utf-8')

        ne_tagged_sentences = stanford_tagger.tag_sents(tokenized_sents)
        for ne_tagged_sentence in ne_tagged_sentences:
            entities_per_sentence = collections.defaultdict(int)
            for tag, chunk in itertools.groupby(ne_tagged_sentence, lambda x: x[1]):
                if tag != 'O':
                    entities_per_sentence[(tag, ' '.join(w for w, t in chunk))] += 1
            entities.append(entities_per_sentence)

    return entities


def textrank(text, window_size=4, ratio=0.05, cutoff=None, as_list=False):
    """
    Simplified version of TextRank:
      - Without POS tagging (we use every word that passes the analyzer instead);
      - Without keyword sequence collapsation (we don't need multi-word keywords,
        because we focus on term-based indexing)
    """

    assert ratio is None or cutoff is None, "Only one of ratio or cutoff can be provided."

    tokens = analyze(text)
    graph = OrderedDict()

    for n in range(len(tokens)-1):
        window = tokens[n:n+window_size]
        for i in range(len(window)):
            if not window[i] in graph:
                graph[window[i]] = OrderedDict()

            for j in range(len(window)):
                if i >= j:
                    continue

                if not window[j] in graph:
                    graph[window[j]] = OrderedDict()

                graph[window[i]][window[j]] = 1

    g = igraph.Graph(directed=False)
    g.add_vertices(iter(graph.keys()))
    edges = [(source, target) for source in graph.keys() for target in graph[source].keys()]
    g.add_edges(edges)
    g.vs['pr'] = g.pagerank()

    if ratio is not None:
        cutoff = round(g.vcount() * ratio)

    keywords = []
    for i, v in enumerate(sorted(g.vs, key=lambda v: v['pr'], reverse=True)):
        if i >= cutoff:
            break
        keywords.append(v['name'])

    if as_list:
        return keywords
    return '\n'.join(keywords)


if __name__ == '__main__':
    texts = [
        """
        Tron: Legacy is a 2010 American science fiction action film directed by Joseph Kosinski, in his feature
        directorial debut, from a screenplay written by Adam Horowitz and Edward Kitsis, based on a story by
        Horowitz, Kitsis, Brian Klugman and Lee Sternthal. It is a sequel to the 1982 film Tron, whose director
        Steven Lisberger returned to produce. The cast includes Jeff Bridges and Bruce Boxleitner reprising their
        roles as Kevin Flynn and Alan Bradley, respectively, as well as Garrett Hedlund, Olivia Wilde, James Frain,
        Beau Garrett and Michael Sheen. The story follows Flynn's adult son Sam, who responds to a message from his
        long-lost father and is transported into a virtual reality called "The Grid, " where Sam, his father, and
        the algorithm Quorra must stop the malevolent program Clu from invading the real world.""",

        """
        Back to the Future is a 1985 American science fiction film directed by Robert Zemeckis and written by
        Zemeckis and Bob Gale. It stars Michael J. Fox as teenager Marty McFly, who accidentally travels back
        in time from 1985 to 1955, where he meets his future parents and becomes his mother's romantic interest.
        Christopher Lloyd portrays the eccentric scientist Dr. Emmett "Doc" Brown, inventor of the time-traveling
        DeLorean, who helps Marty repair history and return to 1985. The cast also includes Lea Thompson as Marty's
        mother Lorraine, Crispin Glover as his father George, and Thomas F. Wilson as Biff Tannen, Marty and George's
        arch-nemesis.

        Zemeckis and Gale wrote the script after Gale wondered whether he would have befriended his father if they had
        attended school together. Film studios rejected it until the financial success of Zemeckis' Romancing the
        Stone. Zemeckis approached Steven Spielberg, who agreed to produce the project at Amblin Entertainment, with
        Universal Pictures as distributor. Fox was the first choice to play Marty, but he was busy filming his
        television series Family Ties, and Eric Stoltz was cast; after the filmmakers decided he was wrong for the
        role, a deal was struck to allow Fox to film Back to the Future without interrupting his television schedule.

        Back to the Future was released on July 3, 1985 and it grossed over $381 million worldwide, becoming the
        highest-grossing film of 1985. It won the Hugo Award for Best Dramatic Presentation, the Saturn Award for Best
        Science Fiction Film, and the Academy Award for Best Sound Effects Editing. It received three Academy Award
        nominations, five BAFTA nominations, and four Golden Globe nominations, including Best Motion Picture (Musical
        or Comedy). In 2007, the Library of Congress selected it for preservation in the National Film Registry, and in
        June 2008 the American Film Institute's special AFI's 10 Top 10 designated it the 10th-best science fiction
        film. The film began a franchise including two sequels, Back to the Future Part II (1989) and Back to the
        Future Part III (1990), an animated series, a theme park ride, several video games, a number of comic books,
        and an upcoming stage musical."""
    ]

    for text in texts:
        print(re.sub(r'\s+', ' ', text))
        keywords = textrank(text)
        print("\nKEYWORDS:")
        for keyword in keywords:
            print(" - %s" % keyword)
        print()
