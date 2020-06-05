#!/bin/sh

list_path=$(mktemp)
mongo --quiet army_ant clean_spool.js > $list_path
find /opt/army-ant/eval/spool -type f | grep -v -f $list_path | xargs rm -v 2>/dev/null || echo "Nothing to remove."
rm $list_path
