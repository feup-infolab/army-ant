#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo_dbpedia" \
    --index-location "/opt/army-ant/indexes/wapo-sample/hgoe-dbpedia-context" \
    --index-type "hgoe:context" \
    --features-location "/opt/army-ant/features/inex_2009_3t_nl" \
    --limit 1000