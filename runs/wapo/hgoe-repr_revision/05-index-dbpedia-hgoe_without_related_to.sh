#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo_dbpedia" \
    --index-location "/opt/army-ant/indexes/wapo/hgoe-dbpedia-without_related_to" \
    --index-type "hgoe:skip_related_to"