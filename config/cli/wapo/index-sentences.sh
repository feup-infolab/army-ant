#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo" \
    --index-location "/opt/army-ant/indexes/wapo-sample-sents" \
    --index-type "hgoe:sents" \
    --limit 1000