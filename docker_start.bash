#!/bin/bash
docker start ping_influxdb
docker start ping_mariadb
docker start ping_collector
docker start ping_web
docker start ping_probe
docker start ping_nginx
