#!/bin/sh

default_query="rock music"

#ranking_params="k1=1.2,b=0.75"
ranking_params="k1=1.2,b=0.75,feature=pr,w=1.8,k=1.0,a=0.6"

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/wapo/lucene_features" \
    --index-type "lucene_features" \
    --ranking-function "bm25" \
    --ranking-params "${PARAMS:-$ranking_params}" \
    --query "${QUERY:-$default_query}" \
    --limit 25