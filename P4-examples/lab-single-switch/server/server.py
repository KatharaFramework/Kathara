#!/usr/bin/env python

import socket


TCP_IP = '20.0.0.2'
TCP_PORT = 5005
BUFFER_SIZE = 20  # Normally 1024, but we want fast response

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()
print ("Connection address:", addr)
while 1:
    data = conn.recv(BUFFER_SIZE)
    if not data: break
    print ("received ", data.decode())
    conn.send(data)  #echo
conn.close()
