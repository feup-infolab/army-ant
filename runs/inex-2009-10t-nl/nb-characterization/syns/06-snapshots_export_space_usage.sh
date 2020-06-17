#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-syns.csv"

base_dir="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-syns-snapshots"
index_type="hgoe:syns"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-syns-snapshots"

snapshots_export_space_usage $base_dir $index_type $base_outdir