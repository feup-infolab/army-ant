#!/bin/sh

time ./army-ant.py features word2vec_simnet \
    --source-path "$HOME/Data/inex-2009-3t-nl/corpus" \
    --source-reader "inex_dir" \
    --output-location "/opt/army-ant/features/inex_2009_3t_nl"