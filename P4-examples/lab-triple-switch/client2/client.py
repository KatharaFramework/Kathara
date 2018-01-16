#!/usr/bin/env python

import socket

TCP_IP = '20.0.0.2'
TCP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

print ("Client connect!")
check = True
i=0
PACKET='packet'

while check:
    cond = input('Send packet flow? (y/n): ')
    if cond.lower() == "y":
        s.send(bytes(PACKET, 'utf-8'))
        RECV= s.recv(BUFFER_SIZE)
        print (RECV.decode(), i)
        i=i+1
    else:
        check = False

s.close()
print ("Client disconnect!")