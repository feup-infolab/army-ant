#!/bin/sh

. $(dirname "$0")/../../../lib/nb-characterization/common.sh

index_path="/opt/army-ant/indexes/inex-2009-10t-nl/hgoe-context_52t_nl"
index_type="hgoe:context"
base_outdir="/opt/army-ant/analysis/inex_2009_10t_nl-context_52t_nl-stats"

export_stats $index_path $index_type $base_outdir