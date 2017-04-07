#!/bin/bash

# TODO check suid

sudo true

sudo chmod 755 $NETKIT_HOME/lstart.sh
sudo chmod 755 $NETKIT_HOME/lclean.sh
sudo chmod 755 $NETKIT_HOME/lcrash.sh
sudo chmod 755 $NETKIT_HOME/lhalt.sh
sudo chmod 755 $NETKIT_HOME/linfo.sh

sudo docker rmi -f netkit
sudo docker build -t netkit $NETKIT_HOME
