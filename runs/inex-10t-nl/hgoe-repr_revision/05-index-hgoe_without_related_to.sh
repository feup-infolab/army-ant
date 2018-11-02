#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-dbpedia-without_related_to" \
    --index-type "hgoe:skip_related_to"