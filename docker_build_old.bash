#!/bin/bash
docker build -t ping:base -f Dockerfile-base .
docker build -t ping:probe -f Dockerfile-probe .
docker build -t ping:collector -f Dockerfile-collector .
docker build -t ping:web -f Dockerfile-web .
docker build -t ping:nginx -f Dockerfile-nginx .
