#!/bin/sh

. $(dirname "$0")/../../lib/nb-characterization/common.sh

index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-degree"

export_degrees $index_path $base_outdir