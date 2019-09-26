#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009/corpus" \
    --source-reader "inex_dir" \
    --index-location "/tmp" \
    --index-type "null_index" \
    --features-location "/opt/army-ant/features/inex_2009" \
    --db-name "aa_inex"
