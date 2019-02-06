#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo" \
    --index-location "/opt/army-ant/indexes/wapo/lucene_features" \
    --index-type "lucene_features" \
    --features-location "/opt/army-ant/features/wapo"