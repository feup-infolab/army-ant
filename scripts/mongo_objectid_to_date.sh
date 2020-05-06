#!/bin/sh

if [ $# -lt 1 ]
then
  echo Usage: $0 OBJECTID
  exit 1
fi

date=$(mongo --quiet --eval "new ObjectId('$1').getTimestamp().toISOString()")
(echo -n $date | xclip -selection c) && echo "$1 has ISO date $date (copied to clipboard)"
