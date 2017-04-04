#!/bin/bash
# TODO pass args with "$@"

python $NETKIT_HOME/python/check.py | echo -ne

sudo true
python $NETKIT_HOME/python/lstart.py "$PWD/" | while read in; do (sudo xterm -e "$in" &); done