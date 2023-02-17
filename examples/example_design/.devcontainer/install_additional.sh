#!/bin/sh

WHEEL_DIR="/tmp/wheels"

if [ -z "$(ls $WHEEL_DIR)" ]; then
    echo "Installing packages from network"
    pip3 install -r /tmp/requirements.txt
else
    echo "Installing wheels from local files"
    pip3 install --find-links="${WHEEL_DIR}/" -r /tmp/requirements.txt
fi
