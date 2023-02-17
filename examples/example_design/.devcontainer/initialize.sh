#!/bin/sh

CONFIG_DIR=$(dirname $(readlink -f $0))
EXAMPLE_CREDS_FILE=$CONFIG_DIR/creds.example.env
CREDS_FILE=$CONFIG_DIR/creds.env

if [ ! -f $CREDS_FILE ] ; then
    cp $EXAMPLE_CREDS_FILE $CREDS_FILE
fi
