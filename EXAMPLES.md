# Indexing a supported collection

We have created a tiny sample of the INEX 2009 Wikipedia Collection, called INEX 2009 3T-NL, based on a uniformly at random selection of 3 topics from the `inex2010.qrels` file.

In order to index this collection using the `INEXDirectoryReader` and the `LuceneEngine`, we run the following command (we used `time` to monitor the run time of the process):

```bash
time ./army-ant.py index /opt/army-ant/collections/inex-2009-3t-nl/corpus inex_dir /opt/army-ant/data/inex-3t-nl/lucene lucene
```

In order to also create and index based on the  `HypergraphOfEntity`, we run:

```
time ./army-ant.py index /opt/army-ant/collections/inex-2009-3t-nl/corpus inex_dir /opt/army-ant/data/inex-3t-nl/hypergraph-of-entity hgoe
```

