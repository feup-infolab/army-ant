#!/bin/sh

default_query="rock music"

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-10t-nl/lucene" \
    --index-type "lucene" \
    --db-name "aa_inex" \
    --query "${QUERY:-$default_query}"