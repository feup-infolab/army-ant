#!/bin/sh

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009/lucene_entities-keywords_5" \
    --index-type "lucene_entities:keywords" \
    --query-type "entity" \
    --db-name "aa_inex" \
    --query "La Bamba||Mr. Tambourine Man"