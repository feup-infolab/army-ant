#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-10t-nl/hgoe-context" \
    --index-type "hgoe:context" \
    --features-location "/opt/army-ant/features/inex_2009_52t_nl"