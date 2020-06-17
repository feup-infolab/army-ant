#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-syns.csv"

index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-syns"
index_type="hgoe:syns"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-syns-stats"

export_stats $index_path $index_type $base_outdir