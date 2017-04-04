#!/bin/bash

python $NETKIT_HOME/python/check.py | echo -ne

M=_machines
L=_links

sudo true
python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do (sudo docker rm -f `cat "$NETKIT_HOME/temp/$in$M"`; rm "$NETKIT_HOME/temp/$in$M"); done
python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do (sudo docker network rm `cat "$NETKIT_HOME/temp/$in$L"`; rm "$NETKIT_HOME/temp/$in$L"); done
