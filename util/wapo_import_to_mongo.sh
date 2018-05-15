#!/bin/bash

if [ $# -lt 1 ]
then
  echo "Usage: $0 TREC_WAPO_CORPUS_DIRECTORY|TREC_WAPO_CORPUS_ARCHIVE"
  exit 1
fi

if [[ $1 == *.tar.gz ]]
then
    if [ ! -f $1 ] || [ ! -r $1 ]
    then
        echo "===> Error: must provide a readable tar.gz file"
        exit 2
    fi

    wapo_dir=$(mktemp -d)
    echo "===> Uncompressing Washington Post to $wapo_dir"
    tar xvzf $1 -C $wapo_dir
else
    wapo_dir=$1
fi

if [ ! -d $wapo_dir ] || [ ! -r $wapo_dir ] || [ ! -x $wapo_dir ]
then
    echo "===> Error: directory must have read and execution permissions"
    exit 3
fi