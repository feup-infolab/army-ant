#!/bin/bash
#
# José Devezas <jld@fe.up.pt>
# FEUP InfoLab and INESC TEC
# 2018-05-15
#

if [ $# -lt 2 ]
then
  echo "Usage: $0 TREC_WAPO_CORPUS_DIRECTORY|TREC_WAPO_CORPUS_ARCHIVE MONGODB_DATABASE"
  exit 1
fi

if [[ $1 == *.tar.gz ]]
then
    if [ ! -f $1 ] || [ ! -r $1 ]
    then
        echo "===> Error: must provide a readable tar.gz file"
        exit 2
    fi

    tmp_dir=$(mktemp -d)
    echo "===> Uncompressing Washington Post v2 to $tmp_dir"
    tar xvzf $1 -C $tmp_dir
    wapo_dir="$tmp_dir/WashingtonPost.v2"
else
    wapo_dir=$1
fi

if [ ! -d $wapo_dir ] || [ ! -r $wapo_dir ] || [ ! -x $wapo_dir ]
then
    echo "===> Error: directory must have read and execution permissions"
    exit 3
fi

db_name=$2

echo "===> Importing all documents to MongoDB database $db_name"
mongoimport --db $db_name --collection documents --type json --maintainInsertionOrder \
    $wapo_dir/data/TREC_Washington_Post_collection.v2.jl

if [ ! -z ${tmp_dir+x} ]
then
    echo "===> Removing temporary directory $tmp_dir"
    rm -rf $tmp_dir
fi

echo "===> Copying articles to a new collection"
mongo $db_name --quiet --eval 'db.documents.aggregate([ { $match: { type: "article" } }, { $out: "articles" } ])'

echo "===> Copying blog posts to a new collection"
mongo $db_name --quiet --eval 'db.documents.aggregate([ { $match: { type: "blog" } }, { $out: "blog_posts" } ])'

echo "===> Deleting documents collection"
mongo $db_name --quiet --eval 'db.documents.drop()'