#!/bin/sh

. $(dirname "$0")/../../lib/nb-characterization/common.sh

index_path="/opt/army-ant/indexes/inex-2009-3t-nl/hgoe"
base_outdir="/opt/army-ant/analysis/inex_2009_3t_nl-stats"

export_degrees $index_path $base_outdir