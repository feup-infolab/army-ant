# Indexing a supported collection

We have created a tiny sample of the INEX 2009 Wikipedia Collection, called INEX 2009 3T-NL, based on a uniformly at random selection of 3 topics from the `inex2010.qrels` file.

In order to index this collection using the `INEXDirectoryReader` and the `LuceneEngine`, we run the following command (we used `time` to monitor the run time of the process):

```bash
$ time ./army-ant.py index --source-path=/opt/army-ant/collections/inex-2009-3t-nl/corpus --source-reader=inex_dir --index-location=/opt/army-ant/data/inex-3t-nl/lucene --index-type=lucene --db-name=inex

...

./army-ant.py index  --source-reader=inex_dir  --index-type=lucene   77.77s user 1.40s system 104% cpu 1:15.63 total
```

We also create an index based on the  `HypergraphOfEntity`. Since it's for the same collection, there is no need to set `db-name` in order to, once again, store the documents metadata in MongoDB (the default database). We run:

```bash
$ time ./army-ant.py index --source-path=/opt/army-ant/collections/inex-2009-3t-nl/corpus --source-reader=inex_dir --index-location=/opt/army-ant/data/inex-3t-nl/hypergraph-of-entity --index-type=hgoe

...


```

