#!/bin/sh

./army-ant.py inspect \
    --index-location "/opt/army-ant/indexes/wapo-sample" \
    --index-type "hgoe" \
    --feature "list-hyperedges" \
    | less