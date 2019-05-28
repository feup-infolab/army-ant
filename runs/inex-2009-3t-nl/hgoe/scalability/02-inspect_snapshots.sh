#!/bin/sh

base_dir="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe-snapshots"
base_outdir="/opt/army-ant/analysis/inex_2009_3t_nl-snapshots"

for snapshot_name in $(ls $base_dir | sort)
do
    echo "==> Inspecting $snapshot_name"

    time ./army-ant.py inspect \
        --index-location "$base_dir/$snapshot_name" \
        --index-type "hgoe" \
        --workdir "$base_outdir/$snapshot_name" \
        --feature "export-node-degree"

    time ./army-ant.py inspect \
        --index-location "$base_dir/$snapshot_name" \
        --index-type "hgoe" \
        --workdir "$base_outdir/$snapshot_name" \
        --feature "export-edge-degree"
done