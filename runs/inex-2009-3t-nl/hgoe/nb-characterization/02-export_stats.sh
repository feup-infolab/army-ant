#!/bin/sh

index_path="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe"
base_outdir="/opt/army-ant/analysis/inex_2009_3t_nl-stats"

echo "==> Exporting global stats"

time ./army-ant.py inspect \
    --index-location "$index_path" \
    --index-type "hgoe" \
    --workdir "$base_outdir" \
    --feature "export-stats"