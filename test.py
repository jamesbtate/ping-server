#!/usr/bin/python3
from pyping import Ping
import time

p = Ping('192.168.0.1', 500, 50)
start = time.time()
results = p.run(1)
stop = time.time()
print("Sent:", results.send_count, "Lost:", results.packet_lost, "Duration: {:.5f}".format(stop-start))
print("Average RTT:", results.avg_rtt, "ms")
#for line in results.output:
#    print(line)
