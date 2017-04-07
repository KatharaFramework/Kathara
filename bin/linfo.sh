#!/bin/bash

python $NETKIT_HOME/python/check.py | echo -ne

M=_machines

sudo true
python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do (sudo docker stats `cat "$NETKIT_HOME/temp/$in$M"`); done