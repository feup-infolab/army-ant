#!/bin/sh

export_degrees() {
    index_path=$1
    index_type=$2
    base_outdir=$3

    echo "==> Exporting node and hyperedge degree"

    time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-node-degree"

    time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-edge-cardinality"
}

export_stats() {
    index_path=$1
    index_type=$2
    base_outdir=$3

    echo "==> Exporting global stats"

    time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-stats"
}

snapshots_index() {
    source_path=$1
    index_path=$2
    index_type=$3
    snapshots_num_docs=$4
    extra_args=$5

    snapshot=1

    for num_docs in $snapshots_num_docs
    do
        snapshot_name="snapshot_$(printf '%.3d' $snapshot)_$num_docs"

        echo "==> Indexing snapshot $snapshot ($snapshot_name)"

        time ./army-ant.py index \
            --source-path "$source_path" \
            --source-reader "inex_dir" \
            --index-location "$index_path/$snapshot_name" \
            --index-type "$index_type" \
            --limit $num_docs \
            $extra_args

        snapshot=$(($snapshot + 1))
    done
}

snapshots_export_degrees() {
    base_dir=$1
    index_type=$2
    base_outdir=$3

    for snapshot_name in $(ls $base_dir | sort)
    do
        echo "==> Exporting node and hyperedge degrees for $snapshot_name"

        time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-node-degree"

        time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-edge-cardinality"
    done
}

snapshots_export_stats() {
    base_dir=$1
    index_type=$2
    base_outdir=$3

    for snapshot_name in $(ls $base_dir | sort)
    do
        echo "==> Exporting node and hyperedge statistics for $snapshot_name"

        time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-stats"
    done
}

snapshots_export_space_usage() {
    base_dir=$1
    index_type=$2
    base_outdir=$3

    for snapshot_name in $(ls $base_dir | sort)
    do
        echo "==> Exporting node and hyperedge space usage for $snapshot_name"

        time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-space-usage"
    done
}
