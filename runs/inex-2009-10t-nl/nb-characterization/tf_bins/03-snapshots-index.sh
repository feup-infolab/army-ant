#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

source_path="/opt/army-ant/collections/inex-2009-10t-nl/corpus"
index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-tf_bins-snapshots"
index_type="hgoe:tf_bins"
snapshots_num_docs="1 2 3 4 5 10 25 50 100 1000 2000 3000 5000 8000"
extra_args='--features-location "/opt/army-ant/features/inex_2009_52t_nl"'

snapshots_index $source_path $index_path $index_type "$snapshots_num_docs"