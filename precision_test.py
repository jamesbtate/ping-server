#!/usr/bin/python3
import time

def measure():
    t0 = time.time()
    t1 = t0
    while t1 == t0:
        t1 = time.time()
    return (t0, t1, t1-t0)

samples = [measure() for i in range(10)]

for s in samples:
    print(s[0],s[1],"{:.8f}".format(s[2]))
