#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009/tfr-keywords" \
    --index-type "tfr:keywords" \
    --features-location "/opt/army-ant/features/inex_2009"