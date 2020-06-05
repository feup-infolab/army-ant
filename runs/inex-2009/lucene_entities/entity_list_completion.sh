#!/bin/sh

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009/lucene_entities" \
    --index-type "lucene_entities" \
    --query-type "entity" \
    --db-name "aa_inex" \
    --query "La Bamba||Mr. Tambourine Man"