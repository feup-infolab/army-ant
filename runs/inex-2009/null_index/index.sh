#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "/tmp" \
    --index-type "null_index" \
    --db-name "aa_inex"
