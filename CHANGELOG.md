# Changelog

## 0.5

* Fixed several major bugs with the evaluation module, where the metrics were not being correctly computed.
* Added a new TensorFlow Ranking engine for introducing a learning to rank baseline.
* Added a new Lucene features engine, based on `LuceneEngine` and the new Lucene's `FeaturesField`.
* Added an `entities` field to extended documents, as an option to index unlinked entities.
* Removed the ability to define blank nodes (use `entities` instead).
* Readers:
  * Added `inex_dbpedia` and `inex_dir_dbpedia` readers that expand INEX triples with DBpedia.
* `HypergraphOfEntity`:
  * Introduced two new `related_to` hyperedge versions: `related_to_by_doc` and `related_to_by_subj`.
  * Added back the option to use an `UNDIRECTED_RANDOM_WALK` for ranking, ignoring hyperedge direction.
* Updated rank correlation analysis call to index method and improved the resume process.
* Small overall improvements: features, server (front-end).

## 0.4

* Added a reader for TREC Washington Post Corpus for TREC 2018 Common Core Track.
* Added Wikidata and DBpedia utility functions to retrieve entities and triples.
* Added a Aho-Corasick method for named entity recognition based on string-searching within a dictionary of entities.
* Added the option to select different retrieval tasks:
  * Document retrieval;
  * Entity retrieval;
  * Term retrieval.
* Changed the Hypergraph-of-Entity engine's search method to rank document nodes instead of entity nodes, when doing document retrieval.
  * In the previous version of the Hypergraph-of-Entity, the document retrieval task was implemented as the ranking of entity nodes, which directly represented a document (e.g., Wikipedia concepts). We revised this process to rank document nodes, ensuring that the search process is generalizable. This will enable us to explicitly implement entity ranking as a task in the future.
* Added a TREC evaluation option that currently processes a set of topics, but does not yet support model assessment based on a qrels relevance judgment file. Results are included in the ZIP file, following the TREC submission format for runs.

## 0.3.3

* Improved the Hypergraph-of-Entity by switching `Document` hyperedges to undirected, adding node and hyperedge weights and introducing a new pruning approach.
  * Pruning required the deletion of directed hyperedges, which was not supported by the `Grph` library. This was forked and implemented. We now use our own custom version of [Grph](https://github.com/jldevezas/Grph).

* Implemented a Biased Random Walk Score, using node and hyperedge weights to randomly traverse the hypergraph.
  * Also improved random sampling efficiency and implemented a new non-uniform random sampler.

* Introduced the `analysis` module, with a new Random Walk stability test based on Kendall's coefficient of concordance W.

* Created an Hypergraph-of-Entity inspection method to export node and hyperedge weights to CSV for external analysis.

* Improved the R graph analysis utility for studying the discriminative power of node and hyperedge weights, based on the exported CSVs from `inspect`.
  * Also added a script to explore functions in order to build node and hyperedge weighting functions. This will also be helpful to build ranking functions later on.

* The reachability index has been disabled.
  * The `entityWeight` has mostly been deprecated (it does not scale) and doing this will save memory.

* Created a partial port of the Hypergraph-of-Entity in C++ and integrated it with the Python tool using Boost Python to create a C++ Python library.
  * The C++ implementation has already been deprecated and serves as an integration example.

* Added overall configurations for the selection of ranking function.

* Fixed several issues with the Dockerfile and automated Docker Hub builds.

* Fixed MongoDB issues with the storage of keys with a period.
