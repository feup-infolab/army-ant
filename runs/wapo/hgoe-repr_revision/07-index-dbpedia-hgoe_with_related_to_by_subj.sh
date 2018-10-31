#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo_dbpedia" \
    --index-location "/opt/army-ant/indexes/wapo/hgoe-dbpedia-with_related_to_by_subj" \
    --index-type "hgoe:related_to_by_subj"