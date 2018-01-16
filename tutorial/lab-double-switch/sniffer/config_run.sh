#!/bin/bash
# fix tcpdump & L4

mv /usr/sbin/tcpdump /usr/bin/tcpdump
ln -s /usr/bin/tcpdump /usr/sbin/tcpdump

ethtool --offload  eth0  rx off  tx off

echo "> Ready!!"