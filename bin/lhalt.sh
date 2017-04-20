#!/bin/bash

python $NETKIT_HOME/python/check.py "$PWD/" $@

export RC=$?
if [ "$RC" = "0" ]; then

    M=_machines

    python $NETKIT_HOME/python/folder_hash.py "$PWD/" $@ | while read in; do ($NETKIT_HOME/wrapper/bin/netkit_dw stop `cat "$NETKIT_HOME/temp/$in$M"`); done

else
    echo FAILED
fi
