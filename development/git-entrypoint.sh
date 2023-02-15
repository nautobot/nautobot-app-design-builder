#!/bin/sh

set -e

DEFAULT_BRANCH=main
wd=`pwd`
mkdir -p /internal/repos
if [ -e /repos ] ; then
  for repo in `ls /repos` ; do
    case $repo in
      *.git) name=$repo ;;
      *) name=${repo}.git ;;
    esac

    if [ -e /internal/repos/$name ] ; then
      rm -rf /internal/repos/$name
    fi

    cd /internal/repos
    git init --bare $name --initial-branch=$DEFAULT_BRANCH
    cp -r /repos/$repo /tmp/$repo
    cd /tmp/$repo
    git init

    git config user.email "operator@company.com"
    git config user.name "Operator"

    git add .

    git commit -m "Initial Commit"
    git branch -M $DEFAULT_BRANCH
    git remote add origin /internal/repos/$name
    git push -u origin $DEFAULT_BRANCH

    rm -rf /tmp/$repo
  done
fi
cd $wd
git-http-server -p 3000 /internal/repos