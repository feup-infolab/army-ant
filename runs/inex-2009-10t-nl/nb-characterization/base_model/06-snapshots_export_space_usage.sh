#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-base_model.csv"

base_dir="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-snapshots"
index_type="hgoe"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-snapshots"

snapshots_export_space_usage $base_dir $index_type $base_outdir