#!/bin/bash

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    res=$(./detect_hardware_linux.sh)
elif [[ "$OSTYPE" == "darwin" ]]; then
    res="x264" # Apple doesn't expose QSV on Intel-based platform
else
    res="x264"
fi
echo $res
