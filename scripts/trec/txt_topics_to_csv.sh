#!/bin/bash
#
# txt_topics_to_csv.sh
# José Devezas <joseluisdevezas@gmail.com>
# 2019-01-16

if [ $# -lt 2 ]
then
    echo "Usage: $0 INPUT_TXT OUTPUT_TXT"
    exit 1
fi

input_filename=$1
output_filename=$2

echo "==> Reading from $input_filename"
cat $input_filename | awk '
    match($0, /<num> Number: ([0-9]+) <\/num>/, m) { OUT=m[1] }
    /<title>/ { getline; print OUT "\t" $0 }' > $output_filename
echo "==> Written to $output_filename"