#!/bin/sh

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009/lucene_entities" \
    --index-type "lucene_entities" \
    --query-type "keyword" \
    --db-name "aa_inex" \
    --query "music"