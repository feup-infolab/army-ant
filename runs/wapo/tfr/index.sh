#!/bin/sh

time ./army-ant.py index \
    --source-path "wapo" \
    --source-reader "wapo" \
    --index-location "/opt/army-ant/indexes/wapo/tfr" \
    --index-type "tfr" \
    --features-location "/opt/army-ant/features/wapo"