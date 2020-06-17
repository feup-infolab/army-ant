#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh
STATS_CSV="$HOME/army_ant-run_stats-tf_bins.csv"

features_path=$(mktemp -d)
bin_sizes=$(printf "%.2d\n" $(seq 2 10))

for bin_size in $bin_sizes
do
    config_dir=$features_path/bins_$bin_size
    mkdir $config_dir
    echo "bins: $bin_size" > $config_dir/tf_bins.yml

    source_path="/opt/army-ant/collections/inex-2009-10t-nl/corpus"
    index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins_$bin_size-snapshots"
    index_type="hgoe:tf_bins"
    snapshots_num_docs="1 2 3 4 5 10 25 50 100 1000 2000 3000 5000 8000"
    extra_args="--features-location $config_dir"

    snapshots_index $source_path $index_path $index_type "$snapshots_num_docs" "$extra_args"
done

rm -rf "$features_path"