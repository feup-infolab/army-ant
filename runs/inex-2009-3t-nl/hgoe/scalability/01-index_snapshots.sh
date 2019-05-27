#!/bin/sh

snapshots_num_docs="1 2 3 4 5 10 25 50 100 250 1000 1500 2000 3000"

snapshot=1

for num_docs in $snapshots_num_docs
do
    snapshot_name="snapshot_$(printf '%.3d' $snapshot)_$num_docs"

    echo "===> Indexing snapshot $snapshot ($snapshot_name)"

    time ./army-ant.py index \
        --source-path "/opt/army-ant/collections/inex-2009-3t-nl/corpus" \
        --source-reader "inex_dir" \
        --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/hgoe-snapshots/$snapshot_name" \
        --index-type "hgoe" \
        --limit $num_docs

    snapshot=$(($snapshot + 1))
done