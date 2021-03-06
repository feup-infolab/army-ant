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
    echo "===> Uncompressing Washington Post to $tmp_dir"
    tar xvzf $1 -C $tmp_dir
    wapo_dir="$tmp_dir/WashingtonPost"
else
    wapo_dir=$1
fi

if [ ! -d $wapo_dir ] || [ ! -r $wapo_dir ] || [ ! -x $wapo_dir ]
then
    echo "===> Error: directory must have read and execution permissions"
    exit 3
fi

db_name=$2

echo "===> Importing articles to MongoDB database $db_name"

for file in $wapo_dir/data/TREC_article_*
do
    echo "===> $file"
    mongoimport --db $db_name --collection articles --type json --maintainInsertionOrder $file
done

echo "===> Importing blog posts to MongoDB database $db_name"

for file in $wapo_dir/data/TREC_blog_*
do
    echo "===> $file"
    mongoimport --db $db_name --collection blog_posts --type json --maintainInsertionOrder $file
done

if [ ! -z ${tmp_dir+x} ]
then
    echo "===> Removing temporary directory $tmp_dir"
    rm -rf $tmp_dir
fi
