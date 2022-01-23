#!/usr/bin/env bash
BRANCH="$(cat .git/HEAD | awk '{print $NF}')"
FETCH_HEAD="$(cat .git/FETCH_HEAD | head -1 | awk '{print $1}')"
sed -i "s|GIT_BRANCH|${BRANCH}|g" templates/about.html
sed -i "s|GIT_COMMIT|${FETCH_HEAD}|g" templates/about.html
