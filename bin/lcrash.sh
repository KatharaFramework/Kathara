#!/bin/bash

python $NETKIT_HOME/python/check.py | echo -ne

sudo true
python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do (cat "($in)_machines" | sudo docker rm -f; rm "($in)_machines"); done
python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do (cat "($in)_links" | sudo docker network rm; rm "($in)_links"); done