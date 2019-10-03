#!/bin/sh

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/lucene_entities-keywords" \
    --index-type "lucene_entities:keywords" \
    --db-name "aa_inex" \
    --query "rock music"