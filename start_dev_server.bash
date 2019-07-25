#!/bin/bash
#
# Start probe.py, server.py and webserver.py for development/testing
# Runs processes in the background with:
#   nohup *program* &
# probe.py is run with sudo because it needs root to use ICMP.
#
nohup ./server.py &
sudo nohup ./probe.py &
nohup ./webserver.py &
sleep 0.5
ps -ef | grep python3 | grep -v grep
