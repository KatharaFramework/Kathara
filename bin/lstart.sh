#!/bin/bash

python $NETKIT_HOME/python/check.py "$PWD/"

export RC=$?
if [ "$RC" = "0" ]; then

    python $NETKIT_HOME/python/print_metadata.py "$PWD/"

    M=_machines

    python $NETKIT_HOME/python/folder_hash.py "$PWD/" | 
    while IFS=';' read -ra in; do ( 
        if [ -f "$NETKIT_HOME/temp/$in$M" ]; 
        then 
            $NETKIT_HOME/wrapper/bin/netkit_dw start `cat "$NETKIT_HOME/temp/$in$M"`; 
                python $NETKIT_HOME/python/lstart.py --execbash $@ "$PWD/" | 
                (while IFS=';' read -ra in; do (xterm -T "${in[0]}" -e "${in[1]}" &); done)
        else 
            python $NETKIT_HOME/python/lstart.py $@ "$PWD/" | while IFS=';' read -ra in; do (xterm -T "${in[0]}" -e "${in[1]}" &); done  
        fi ); 
    done

else
    echo FAILED
fi
