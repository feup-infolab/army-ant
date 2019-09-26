#!/bin/sh

#
# hgoe:keywords => tfr:keywords
#

# time ./army-ant.py search \
#     --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/tfr-keywords" \
#     --index-type "tfr:keywords" \
#     --db-name "aa_inex" \
#     --ranking-function "random_walk" \
#     --ranking-params "l=2,r=1000,nf=0,ef=0,expansion=false,directed=true,weighed=false,base_index_location=/opt/army-ant/indexes/inex-2009-3t-nl/hgoe-keywords,base_index_type=hgoe:keywords" \
#     --query "rock music"

#
# tf_idf
#

time ./army-ant.py search \
    --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/tfr-keywords" \
    --index-type "tfr:keywords" \
    --db-name "aa_inex" \
    --ranking-function "tf_idf" \
    --query "rock music"

#
# bm25(k1=1.2, b=0.75) => tfr:keywords
#

# time ./army-ant.py search \
#     --index-location "/opt/army-ant/indexes/inex-2009-3t-nl/tfr-keywords" \
#     --index-type "tfr:keywords" \
#     --db-name "aa_inex" \
#     --ranking-function "bm25" \
#     --ranking-params "k1=1.2,b=0.75" \
#     --query "rock music"
