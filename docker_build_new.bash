#!/bin/bash
# this script requires docker 17.05 (1.x releases stopper at 1.13 in 2017)
#  for multi-stage builds
docker build --target builder -t ping:builder .
docker build --target base -t ping:base .
docker build --target probe -t ping:probe .
docker build --target collector -t ping:collector .
docker build --target web -t ping:web .
