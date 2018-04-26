#!/usr/bin/python3
from pyping import Ping
import argparse
import rrdtool
import time

p = Ping('192.168.0.1', 500, 50)
start = time.time()
count = 0
try:
    while True:
        results = p.run(1)
        rrdtool.update("test1.rrd", "N:" + str(results.avg_rtt))
        count += 1
        current = time.time()
        should = start + count
        if should > current:
            time.sleep(should-current)
except KeyboardInterrupt:
    pass
print("Pinged", count, "times.")
