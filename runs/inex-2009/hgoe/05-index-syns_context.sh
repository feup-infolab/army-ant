#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009/hgoe-syns_context_52t_nl" \
    --index-type "hgoe:syns:context" \
    --features-location "/opt/army-ant/features/inex_2009_52t_nl"