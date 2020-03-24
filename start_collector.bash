#!/bin/bash

python manage.py migrate

python server.py -f
