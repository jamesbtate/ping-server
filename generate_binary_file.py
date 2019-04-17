#!/usr/bin/env python3
import struct
import random
import time

f = open('binary.data.1', 'wb')
for i in range(86400):
    t = int(time.time() + i)
    d = struct.pack('IB', t, random.randint(0,255))
    _ = f.write(d)
f.close()

f = open('binary.data.2', 'wb')
for i in range(86400):
    t = int(time.time() + i)
    d = struct.pack('IB', t, random.randint(20,25))
    _ = f.write(d)
f.close()
