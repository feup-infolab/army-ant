#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-syns"
index_type="hgoe:syns"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-syns-stats"

export_degrees $index_path $index_type $base_outdir