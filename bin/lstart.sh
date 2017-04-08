#!/bin/bash

python $NETKIT_HOME/python/check.py "$PWD/"

export RC=$?
if [ "$RC" = "0" ]; then

    M=_machines

    sudo true
    python $NETKIT_HOME/python/folder_hash.py "$PWD/" | 
    while read in; do ( 
        if [ -f "$NETKIT_HOME/temp/$in$M" ]; 
        then 
            sudo docker start `cat "$NETKIT_HOME/temp/$in$M"`; 
                python $NETKIT_HOME/python/lstart.py --execbash $@ "$PWD/" | 
                (while read in; do (sudo xterm -e "$in" &); done)
        else 
            python $NETKIT_HOME/python/lstart.py $@ "$PWD/" | while read in; do (sudo xterm -e "$in" &); done  
        fi ); 
    done

else
    echo FAILED
fi