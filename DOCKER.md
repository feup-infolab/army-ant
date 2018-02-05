# Docker image

Currently, we provide a [basic image](https://hub.docker.com/r/jldevezas/army-ant/tags/) to experiment with Army ANT 0.3. This image comes prepackaged with two indexes for a small subset of the INEX 2009 Wikipedia Collection. This subset, INEX 2009 3T-NL covers 3 topics (3T) and all the documents mentioned in the relevance judgments for these topics, excluding linked files (NL; i.e., no links). The instance includes the following engines, ranking functions and configurable parameters:

* Lucene
  * TF-IDF
  * BM25
    * k1 = [1, 1.2, 1.8]
    * b = [0.5, 0.75, 1]
  * Divergence From Randomness (DFR)
    * BasicModel: BM = [BE, G, P, D, In, Ine, IF]
    * AfterEffect: AE = [L, B, Disabled]
    * Normalization: N = [H1, H2, H3, Z, Disabled]
* Hypergraph-of-Entity
  * Random Walk Score
    * Length: l = [1, 2, 3, 4, 5, 6]
    * Repeats: r = [10, 100, 250, 500, 750, 1000]
  * Jaccard Score

## Evaluation Files

In order to experiment with the evaluation module, you will first need to download the INEX 2009 3T-NL subset, attached to [release 0.3](https://github.com/feup-infolab/army-ant/releases/tag/0.3), thus obtaining the `topics/2010-topics.xml`, with the test queries, and the `assessments/2010/inex2010.qrels` with the relevance judgments.

## Installation

In order to install Army ANT, please follow the instructions in [army-ant-install](https://github.com/feup-infolab/army-ant-install). Running Army ANT will require a MongoDB docker instance in the same network on the default port.