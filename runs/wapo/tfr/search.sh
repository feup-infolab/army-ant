#!/bin/sh

default_query="rock music"

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/wapo/tfr" \
    --index-type "tfr" \
    --db-name "aa_wapo" \
    --query "${QUERY:-$default_query}"