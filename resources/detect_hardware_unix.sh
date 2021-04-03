#!/bin/bash

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    res=$(./detect_hardware_linux.sh)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    res="VTL"
else
    res="x264"
fi
echo $res
