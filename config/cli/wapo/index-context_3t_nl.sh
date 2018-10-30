#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo" \
    --index-location "/opt/army-ant/indexes/wapo-sample-context" \
    --index-type "hgoe:context" \
    --features-location "/opt/army-ant/features/inex_2009_3t_nl" \
    --limit 1000