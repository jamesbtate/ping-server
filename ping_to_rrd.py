#!/usr/bin/python3
from pyping import Ping
import argparse
import rrdtool
import time
import pwd
import os

desc = "Ping a host every second and log the results to an RRD file."
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("host", help="Host to ping")
parser.add_argument("rrdfile", help="RRD file to store results in")
parser.add_argument("-v", '--verbose', action='store_true',
                    help="RRD file to store results in")
args = parser.parse_args()

# check if we need to make file
try:
    os.stat(args.rrdfile)
except FileNotFoundError:
    # create RRD file
    rrdtool.create(args.rrdfile, "-s", '1', 'DS:ping:GAUGE:2:0:999',
                   'RRA:LAST:0:1:2419200')
    logname = os.getlogin()
    pw = pwd.getpwnam(logname)
    os.chown(args.rrdfile, pw.pw_uid, pw.pw_gid)
    print("Created RRD file", args.rrdfile)

p = Ping(args.host, 500, 50)
start = time.time()
count = 0
seconds = 0 # same as count, but add the number of seconds we spent waiting
received = 0
try:
    while True:
        results = p.run(1)
        count += 1
        seconds += 1
        if results.packet_lost == 0:
            if args.verbose: print("response", results.avg_rtt, "ms")
            rrdtool.update(args.rrdfile, "N:" + str(results.avg_rtt))
            received += 1
        current = time.time()
        should = start + seconds
        if should > current:
            time.sleep(should-current)
        else:
            msg = "Took a long time to do the last cycle: {:.2f} seconds" \
                  .format(current-should+1)
            seconds += int(current-should)
            print(msg)
except KeyboardInterrupt:
    pass
print("Received response from ", args.host, received, 'of', count, "times.")
