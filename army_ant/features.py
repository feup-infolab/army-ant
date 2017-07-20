#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# features.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-07-20

import math
import numpy as np
import tensorflow as tf
from army_ant.text import analyze, bag_of_words
from army_ant.exception import ArmyAntException

class FeatureExtractor(object):
    @staticmethod
    def factory(method, reader, output_location, output_type):
        if method == 'word2vec':
            return Word2Vec(reader, output_location, output_type)
        else:
            raise ArmyAntException("Unsupported method %s" % method)

    def __init__(self, reader, output_location, output_type):
        self.reader = reader
        self.output_location = output_location
        self.output_type = output_type

    def extract(self):
        raise ArmyAntException("Extract not implemented for %s" % self.__class__.__name__)

class Word2Vec(FeatureExtractor):
    def context(self, tokens, n=3):
        token_context = []
        for i in range(n, len(tokens)-n):
            c = [tokens[j] for j in range(i-n, i)]
            c.extend([tokens[j] for j in range(i+1, i+n+1)])
            token_context.append((tokens[i], c))
        return token_context
    
    def preprocess(self):
        vocabulary = set([])
        sentences = []

        for doc in self.reader:
            tokens = analyze(doc.text, remove_stopwords=False)
            print(self.context(tokens))
            sentences.append(tokens)
            vocabulary = vocabulary.union(tokens)

        vocabulary = list(vocabulary)
        self.vocabulary_idx = {}

        for word in vocabulary:
            self.vocabulary_idx[word] = len(self.vocabulary_idx)

    def train(self):
        batch_size = 128
        embedding_size = 128  # Dimension of the embedding vector.
        skip_window = 1       # How many words to consider left and right.
        num_skips = 2         # How many times to reuse an input to generate a label.

        # We pick a random validation set to sample nearest neighbors. Here we limit the
        # validation samples to the words that have a low numeric ID, which by
        # construction are also the most frequent.
        valid_size = 16     # Random set of words to evaluate similarity on.
        valid_window = 100  # Only pick dev samples in the head of the distribution.
        valid_examples = np.random.choice(valid_window, valid_size, replace=False)
        num_sampled = 64    # Number of negative examples to sample.

        vocabulary_size = len(self.vocabulary_idx)

        graph = tf.Graph()

        with graph.as_default():

          # Input data.
          train_inputs = tf.placeholder(tf.int32, shape=[batch_size])
          train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
          valid_dataset = tf.constant(valid_examples, dtype=tf.int32)

          # Ops and variables pinned to the CPU because of missing GPU implementation
          with tf.device('/cpu:0'):
            # Look up embeddings for inputs.
            embeddings = tf.Variable(
                tf.random_uniform([vocabulary_size, embedding_size], -1.0, 1.0))
            embed = tf.nn.embedding_lookup(embeddings, train_inputs)

            # Construct the variables for the NCE loss
            nce_weights = tf.Variable(
                tf.truncated_normal([vocabulary_size, embedding_size],
                                    stddev=1.0 / math.sqrt(embedding_size)))
            nce_biases = tf.Variable(tf.zeros([vocabulary_size]))

          # Compute the average NCE loss for the batch.
          # tf.nce_loss automatically draws a new sample of the negative labels each
          # time we evaluate the loss.
          loss = tf.reduce_mean(
              tf.nn.nce_loss(weights=nce_weights,
                             biases=nce_biases,
                             labels=train_labels,
                             inputs=embed,
                             num_sampled=num_sampled,
                             num_classes=vocabulary_size))

          # Construct the SGD optimizer using a learning rate of 1.0.
          optimizer = tf.train.GradientDescentOptimizer(1.0).minimize(loss)

          # Compute the cosine similarity between minibatch examples and all embeddings.
          norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keep_dims=True))
          normalized_embeddings = embeddings / norm
          valid_embeddings = tf.nn.embedding_lookup(
              normalized_embeddings, valid_dataset)
          similarity = tf.matmul(
              valid_embeddings, normalized_embeddings, transpose_b=True)

          # Add variable initializer.
          init = tf.global_variables_initializer()

        # Step 5: Begin training.
        num_steps = 100001

        with tf.Session(graph=graph) as session:
          # We must initialize all variables before we use them.
          init.run()
          print('Initialized')

          average_loss = 0
          for step in range(num_steps):
            batch_inputs, batch_labels = self.generate_batch(
                batch_size, num_skips, skip_window)
            feed_dict = {train_inputs: batch_inputs, train_labels: batch_labels}

            # We perform one update step by evaluating the optimizer op (including it
            # in the list of returned values for session.run()
            _, loss_val = session.run([optimizer, loss], feed_dict=feed_dict)
            average_loss += loss_val

            if step % 2000 == 0:
              if step > 0:
                average_loss /= 2000
              # The average loss is an estimate of the loss over the last 2000 batches.
              print('Average loss at step ', step, ': ', average_loss)
              average_loss = 0

            # Note that this is expensive (~20% slowdown if computed every 500 steps)
            if step % 10000 == 0:
              sim = similarity.eval()
              for i in xrange(valid_size):
                valid_word = reverse_dictionary[valid_examples[i]]
                top_k = 8  # number of nearest neighbors
                nearest = (-sim[i, :]).argsort()[1:top_k + 1]
                log_str = 'Nearest to %s:' % valid_word
                for k in xrange(top_k):
                  close_word = reverse_dictionary[nearest[k]]
                  log_str = '%s %s,' % (log_str, close_word)
                print(log_str)
          final_embeddings = normalized_embeddings.eval()

    def extract(self):
        self.preprocess()
        self.train()
