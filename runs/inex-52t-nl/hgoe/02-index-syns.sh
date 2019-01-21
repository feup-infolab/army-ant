#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-52t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009-52t-nl/hgoe-syns" \
    --index-type "hgoe:syns"