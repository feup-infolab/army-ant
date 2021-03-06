# Indexing a supported collection

We have created a tiny sample of the INEX 2009 Wikipedia Collection, called INEX 2009 3T-NL, based on a uniformly at random selection of 3 topics from the `inex2010.qrels` file.

In order to index this collection using the `INEXDirectoryReader` and the `LuceneEngine`, we run the following command (we used `time` to monitor the run time of the process):

```bash
$ time ./army-ant.py index \
	--source-path=/opt/army-ant/collections/inex-2009-3t-nl/corpus \
	--source-reader=inex_dir \
	--index-location=/opt/army-ant/data/inex-3t-nl/lucene \
	--index-type=lucene \
	--db-name=inex

...

77.77s user 1.40s system 104% cpu 1:15.63 total
```

We also create an index based on the  `HypergraphOfEntity`. Since it's for the same collection, there is no need to set `db-name` in order to, once again, store the documents metadata in MongoDB (the default database). We run:

```bash
$ time ./army-ant.py index \
	--source-path=/opt/army-ant/collections/inex-2009-3t-nl/corpus \
	--source-reader=inex_dir \
	--index-location=/opt/army-ant/data/inex-3t-nl/hypergraph-of-entity \
	--index-type=hgoe

...

75.60s user 9.44s system 128% cpu 1:06.19 total
```

# Retrieving images for Wikipedia collections

Since this is a Wikipedia collection and there is a `metadata.url` field in the MongoDB object for each document, we can use the `fetch-wikipedia-images` function from the  `extras` command to find the first figure from the corresponding Wikipedia page, so that we can display it in the web interface when searching. The URL to the original image is stored in the `img_url` metadata attribute. We do this by running:

```bash
$ ./army-ant.py extras fetch-wikipedia-images --db-name=inex
```

# Running an analysis method

For example, we implemented an analysis for a random walk stability test, using [Kendall's coefficient of concordance (Kendall W)](https://en.wikipedia.org/wiki/Kendall%27s_W). Each analysis has its own command line arguments. In particular, for `rw-stability`, we run it using:

```bash
$ time ./army-ant.py analysis rw-stability \
    --index-location /opt/army-ant/data/inex-3t-nl/hgoe \
    --index-type hgoe \
    --rw-length=2,3,4 \
    --rw-repeats=100,1000,10000 \
    --topics-path /opt/army-ant/collections/inex-2009-3t-nl/topics/2010-topics.xml \
    --limit 1000 \
    --repeats 100 \
    --output-path /opt/army-ant/analysis/inex_3t_nl-hgoe-rw_stability \
    --method kendall_w
    
...

3391.45s user 15.46s system 227% cpu 24:55.95 total
```