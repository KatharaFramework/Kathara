#!/bin/bash

sudo true

echo "Compiling netkit_dw"
sudo gcc $NETKIT_HOME/wrapper/netkit_dw.c -o $NETKIT_HOME/wrapper/bin/netkit_dw

echo "Setting permissions"
sudo chown root:root $NETKIT_HOME/wrapper/bin/netkit_dw
sudo chmod 4755 $NETKIT_HOME/wrapper/bin/netkit_dw
sudo chattr -i $NETKIT_HOME/wrapper/bin/netkit_dw
sudo chmod 000 $NETKIT_HOME/wrapper/netkit_dw.c

sudo chmod 755 $NETKIT_HOME/lstart.sh
sudo chmod 755 $NETKIT_HOME/lclean.sh
sudo chmod 755 $NETKIT_HOME/lcrash.sh
sudo chmod 755 $NETKIT_HOME/lhalt.sh
sudo chmod 755 $NETKIT_HOME/linfo.sh

echo "Building image"
sudo docker rmi -f netkit
sudo docker build -t netkit $NETKIT_HOME

sudo -k
