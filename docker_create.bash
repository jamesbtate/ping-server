#!/bin/bash
docker create --name ping_influxdb -h influxdb --network ping -p 8086:8086 -v /opt/ping/influxdb/:/var/lib/influxdb influxdb
MYSQL_ROOT_PASSWORD=password
docker create --name ping_mariadb -h mariadb --network ping -p 13306:3306 -v /opt/ping/mariadb/:/var/lib/mysql -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD mariadb:10.3

docker create --name ping_collector -h collector --network ping -p 8765:8765 ping:collector
docker create --name ping_web -h web --network ping -p 5000:5000 ping:web
docker create --name ping_probe -h probe --network ping ping:probe
