#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-base_model.csv"

index_path=/opt/army-ant/indexes/inex-2009-10t-nl/hgoe

time=$(ms_time ./army-ant.py index \
    --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
    --source-reader "inex_dir" \
    --index-location "$index_path" \
    --index-type "hgoe")

echo $index_path,creation,$time >> $STATS_CSV