#!/bin/bash
docker rm -f ping_influxdb
docker rm -f ping_mariadb

docker rm -f ping_collector
docker rm -f ping_web
docker rm -f ping_probe
