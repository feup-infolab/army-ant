#!/bin/sh

# No headers are assigned, but fields should be: index_path, stat, ms_time
STATS_CSV="$HOME/army_ant-run_stats-$(date +%Y%m%dT%H%M).csv"

ms_time() {
    start=$(date +%s.%N)
    $*
    end=$(date +%s.%N)

    python -c "print(round(($end - $start) * 1000))"
}

export_degrees() {
    index_path=$1
    index_type=$2
    base_outdir=$3

    echo "==> Exporting node and hyperedge degree"

    time=$(ms_time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-node-degree")

    echo $index_path,node degree,$time >> $STATS_CSV

    time=$(ms_time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-edge-cardinality")

    echo $index_path,edge cardinality,$time >> $STATS_CSV
}

export_stats() {
    index_path=$1
    index_type=$2
    base_outdir=$3

    echo "==> Exporting global stats"

    time=$(ms_time ./army-ant.py inspect \
        --index-location "$index_path" \
        --index-type "$index_type" \
        --workdir "$base_outdir" \
        --feature "export-stats")

    echo $index_path,global stats,$time >> $STATS_CSV
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

        time=$(ms_time ./army-ant.py index \
            --source-path "$source_path" \
            --source-reader "inex_dir" \
            --index-location "$index_path/$snapshot_name" \
            --index-type "$index_type" \
            --limit $num_docs \
            $extra_args)

        echo $index_path/$snapshot_name,creation,$time >> $STATS_CSV

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

        time=$(ms_time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-node-degree")

        echo $base_dir/$snapshot_name,node degree,$time >> $STATS_CSV

        time=$(ms_time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-edge-cardinality")

        echo $base_dir/$snapshot_name,edge cardinality,$time >> $STATS_CSV
    done
}

snapshots_export_stats() {
    base_dir=$1
    index_type=$2
    base_outdir=$3

    for snapshot_name in $(ls $base_dir | sort)
    do
        echo "==> Exporting global statistics for $snapshot_name"

        time=$(ms_time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-stats")

        echo $base_dir/$snapshot_name,global stats,$time >> $STATS_CSV
    done
}

snapshots_export_space_usage() {
    base_dir=$1
    index_type=$2
    base_outdir=$3

    for snapshot_name in $(ls $base_dir | sort)
    do
        echo "==> Exporting node and hyperedge space usage for $snapshot_name"

        time=$(ms_time ./army-ant.py inspect \
            --index-location "$base_dir/$snapshot_name" \
            --index-type "$index_type" \
            --workdir "$base_outdir/$snapshot_name" \
            --feature "export-space-usage")

        echo $base_dir/$snapshot_name,space usage,$time >> $STATS_CSV
    done
}
