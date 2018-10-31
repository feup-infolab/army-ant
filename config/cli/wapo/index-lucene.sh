#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo" \
    --index-location "/opt/army-ant/indexes/wapo-sample/lucene" \
    --index-type "lucene" \
    --limit 1000