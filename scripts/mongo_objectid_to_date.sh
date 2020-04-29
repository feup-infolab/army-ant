#!/bin/sh

date=$(mongo --quiet --eval "new ObjectId('$1').getTimestamp().toISOString()")
(echo -n $date | xclip -selection c) && echo "$1 has ISO date $date (copied to clipboard)"
