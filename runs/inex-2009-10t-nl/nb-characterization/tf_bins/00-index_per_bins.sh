#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

features_path=$(mktemp -d)
bin_sizes=$(printf "%.2d\n" $(seq 2 10))

for bin_size in $bin_sizes
do
    config_dir=$features_path/bins_$bin_size
    mkdir $config_dir
    echo "bins: $bin_size" > $config_dir/tf_bins.yml

    time ./army-ant.py index \
        --source-path "/opt/army-ant/collections/inex-2009-10t-nl/corpus" \
        --source-reader "inex_dir" \
        --index-location "/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins_$bin_size" \
        --index-type "hgoe:tf_bins" \
        --features-location "$config_dir"
done

rm -rf "$features_path"