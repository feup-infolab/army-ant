#!/bin/sh

. $(dirname "$0")/../../lib/nb-characterization/common.sh

base_dir="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-snapshots"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-snapshots"

snapshots_export_space_usage $base_dir $base_outdir