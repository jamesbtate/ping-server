#!/bin/bash
docker image rm -f ping:base
docker image rm -f ping:probe
docker image rm -f ping:collector
docker image rm -f ping:web
