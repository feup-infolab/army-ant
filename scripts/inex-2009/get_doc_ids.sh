#!/bin/bash

if [ $# -lt 2 ]
then
    echo "Usage: $0 INEX_CORPUS_PATH OUT_DOC_ID_FILE"
    exit 1
fi

corpus_path=$1
out_path=$2

for file in $corpus_path/pages*.tar.bz2
do
    tar tvjf $file
done | awk -f path_to_doc_id.awk > $out_path
