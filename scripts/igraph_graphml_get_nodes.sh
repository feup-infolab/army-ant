#!/bin/bash

if [ $# -lt 1 ]
then
  echo "Usage: $0 GRAPHML_GZIP"
  exit 1
fi

if [ ! -x "$(which zpcregrep)" ]
then
  echo "Error: requires pcregrep to run (zpcregrep not found)"
fi

zpcregrep -o1 '<data key="v_name">(.*?)</data>' $1 | sort -u
