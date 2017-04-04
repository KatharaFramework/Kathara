#!/bin/bash
# TODO pass args with "$@"
sudo true

python $NETKIT_HOME/python/lstart.py "$PWD/" | while read in; do (sudo xterm -e "$in" &); done