#!/bin/sh

. $(dirname "$0")/../../lib/nb-characterization/common.sh

source_path="/opt/army-ant/collections/inex-2009-3t-nl/corpus"
index_path="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe-snapshots"
snapshots_num_docs="1 2 3 4 5 10 25 50 100 250 1000 1500 2000 3000"

snapshots_index source_path $index_path "$snapshots_num_docs"