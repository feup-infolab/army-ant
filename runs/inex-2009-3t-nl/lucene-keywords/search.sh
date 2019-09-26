#!/bin/sh

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/lucene-keywords" \
    --index-type "lucene:keywords" \
    --db-name "aa_inex" \
    --query "rock music"