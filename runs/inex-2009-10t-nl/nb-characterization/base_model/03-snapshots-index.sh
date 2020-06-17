#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-base_model.csv"

source_path="/opt/army-ant/collections/inex-2009-10t-nl/corpus"
index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-snapshots"
index_type="hgoe"
snapshots_num_docs="1 2 3 4 5 10 25 50 100 1000 2000 3000 5000 8000"

snapshots_index $source_path $index_path $index_type "$snapshots_num_docs"