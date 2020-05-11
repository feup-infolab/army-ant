#!/bin/sh

time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009/corpus" \
    --source-reader "inex_dir" \
    --index-location "/opt/army-ant/indexes/inex-2009/hgoe-keywords-tf_bins" \
    --index-type "hgoe:keywords:tf_bins" \
    --features-location "/opt/army-ant/features/inex_2009"