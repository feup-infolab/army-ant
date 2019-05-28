#!/bin/sh

index_path="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe"
base_outdir="/opt/army-ant/analysis/inex_2009_3t_nl-degree"

echo "==> Exporting node and hyperedge degree"

time ./army-ant.py inspect \
    --index-location "$index_path" \
    --index-type "hgoe" \
    --workdir "$base_outdir" \
    --feature "export-node-degree"

time ./army-ant.py inspect \
    --index-location "$index_path" \
    --index-type "hgoe" \
    --workdir "$base_outdir" \
    --feature "export-edge-degree"