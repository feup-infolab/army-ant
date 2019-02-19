#!/bin/sh

time ./army-ant.py analysis rank-concordance \
    --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/hgoe" \
    --index-type "hgoe" \
    --rw-length "2,3,4" \
    --rw-repeats "100,1000,10000" \
    --topics-path "/opt/army-ant/collections/inex-2009-3t-nl/topics/2010-topics.xml" \
    --output-path "/opt/army-ant/analysis/inex_2009_3t_nl-hgoe_rws-rank_concordance" \
    --cutoff 1000 \
    --repeats 100 \
    --method "kendall_w"