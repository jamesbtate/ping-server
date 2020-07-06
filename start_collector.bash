#!/bin/bash -e

python manage.py migrate

python server.py -f
