#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins"
index_type="hgoe:tf_bins"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-tf_bins-stats"

export_stats $index_path $index_type $base_outdir