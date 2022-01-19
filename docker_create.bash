#!/bin/bash
docker create --name ping_influxdb --restart always -h influxdb --network ping -p 8086:8086 -v /opt/ping/influxdb/:/var/lib/influxdb influxdb:1.8
docker create --name ping_mariadb --restart always -h mariadb --network ping -p 13306:3306 -v /opt/ping/mariadb/:/var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD=password \
    -e MYSQL_DATABASE=ping \
    -e MYSQL_USER=ping \
    -e MYSQL_PASSWORD=ping \
    mariadb:10.3

docker create --name ping_collector --restart always -h collector --network ping -p 8765:8765 ping:collector
docker create --name ping_web --restart always -h web --network ping --expose 8000 ping:web
docker create --name ping_nginx --restart always -h nginx --network ping -p 5000:80 ping:nginx
docker create --name ping_probe --restart always -h probe --network ping ping:probe
