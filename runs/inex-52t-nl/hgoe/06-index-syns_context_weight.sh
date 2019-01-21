#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-syns_context_weight" \
    --index-type "hgoe:syns:context:weight" \
    --features-location "/opt/army-ant/features/inex_2009_52t_nl"