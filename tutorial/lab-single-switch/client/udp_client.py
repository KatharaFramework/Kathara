#!/usr/bin/python

import time
from socket import *

for pings in range(10):
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.settimeout(1)
    message = 'test'
    addr = ("20.0.0.2", 12000)

    start = time.time()
    clientSocket.sendto(message, addr)
    try:
        data, server = clientSocket.recvfrom(1024)
        end = time.time()
        elapsed = end - start
        print '%s %d %d' % (data, pings, elapsed)
    except timeout:
        print 'REQUEST TIMED OUT'