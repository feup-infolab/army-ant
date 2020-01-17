#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

base_dir="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins-snapshots"
index_type="hgoe:tf_bins"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-tf_bins-snapshots"

snapshots_export_space_usage $base_dir $index_type $base_outdir