#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo_dbpedia" \
    --index-location "/opt/army-ant/indexes/wapo-sample/hgoe-dbpedia-sents" \
    --index-type "hgoe:sents" \
    --limit 1000