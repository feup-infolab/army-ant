#!/bin/sh

. $(dirname "$0")/../../lib/nb-characterization/common.sh

base_dir="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe-snapshots"
base_outdir="/opt/army-ant/analysis/inex_2009_3t_nl-snapshots"

snapshots_export_stats $base_dir $base_outdir