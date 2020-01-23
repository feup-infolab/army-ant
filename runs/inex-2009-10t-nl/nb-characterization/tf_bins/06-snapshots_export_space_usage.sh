#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

bin_sizes=$(printf "%.2d\n" $(seq 2 10))

for bin_size in $bin_sizes
do
    base_dir="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins_$bin_size-snapshots"
    index_type="hgoe:tf_bins"
    base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-tf_bins_$bin_size-snapshots"

    snapshots_export_space_usage $base_dir $index_type $base_outdir
done