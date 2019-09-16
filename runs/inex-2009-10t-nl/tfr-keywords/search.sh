#!/bin/sh

default_query="rock music"

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009-10t-nl/tfr-keywords" \
    --index-type "tfr" \
    --db-name "aa_inex" \
    --query "${QUERY:-$default_query}"