#!/bin/bash
#
# José Devezas
# FEUP InfoLab and INESC TEC
# 2018-06-25
#

if [ $# -lt 1 ]
then
    echo "Usage: $0 MONGODB_DATABASE"
    exit 1
fi

db_name=$1
mongo --quiet  $db_name wapo_remove_duplicates.js