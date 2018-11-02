#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir_dbpedia" \
    --index-location "/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-dbpedia-with_related_to_by_subj" \
    --index-type "hgoe:related_to_by_subj"