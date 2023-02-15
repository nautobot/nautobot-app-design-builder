#!/bin/sh

CONFIG_DIR=$(dirname $(readlink -f $0))
EXAMPLE_CREDS_FILE=$CONFIG_DIR/creds.example.env
REPO_DIR="${CONFIG_DIR}/../repos"
CREDS_FILE=$CONFIG_DIR/creds.env

if [ ! -f $CREDS_FILE ] ; then
    cp $EXAMPLE_CREDS_FILE $CREDS_FILE
fi

if [ ! -d $REPO_DIR/config-contexts.git ] ; then
    mkdir -p $REPO_DIR
    git init --bare $REPO_DIR/config-contexts.git
    git clone $REPO_DIR/config-contexts.git ../config-contexts
    git -C ../config-contexts/ branch -m main
    touch ../config-contexts/README.md
    git -C ../config-contexts/ add README.md 
    git -C ../config-contexts/ commit -m "Initial Commit"
    git -C ../config-contexts/ push origin main
fi
