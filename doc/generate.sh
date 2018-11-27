#!/bin/bash

if [ ! -x "$(which pyreverse)" ]
then
  echo "Error: pyreverse not found, please install pylint first."
  exit 1
fi

cd "$(dirname "$0")"
pyreverse -o png ../army_ant
