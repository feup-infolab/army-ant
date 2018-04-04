# Feature configurations for indexing

Some of the features, like pruning on the hypergraph-of-entity (i.e., `--index-type=hgoe:weight:prune`) require some parameter configurations (usually in YAML). For example, for pruning, we use a `prune.yml` file to establish thresholds with the minimum weights, below which we remove nodes and hyperedges.

Available examples within this directory include:

* `prune.xml` for `prune` index feature.
