# Docker image

Currently, we provide a basic image to experiment with Army ANT, for version 0.3-rc3. This image comes prepackaged with two indexes for a small subset of the INEX 2009 Wikipedia Collection. This subset, INEX 2009 3T-NL covers 3 topics (3T) and all the documents mentioned in the relevance judgments for these topics, excluding linked files (NL; i.e., no links). The instance includes the following engines, ranking functions and configurable parameters:

* Lucene
  * TF-IDF
  * BM25
    * k1 = [1, 1.2, 1.8]
    * b = [0.5, 0.75, 1]
  * Divergence From Randomness (DFR)
    * BasicModel: BM = [BE, G, P, D, In, Ine, IF]
    * AfterEffect: AE = [L, B, Disabled]
    * Normalization: N = [H1, H2, H3, Z, Disabled]
* Engine: Hypergraph-of-Entity
  * Random Walk Score
    * Length: l = [1, 2, 3, 4, 5, 6]
    * Repeats: r = [10, 100, 250, 500, 750, 1000]
  * Jaccard Score

## Installation instructions

The current version is quite large. We will fix this later, by using `docker-composer` to use separate containers for Python, NodeJS, MongoDB and Army ANT server.

```bash
$ docker pull jldevezas/army-ant:0.3-rc3
$ docker run -p 8080:8080 jldevezas/army-ant:0.3-rc3
```