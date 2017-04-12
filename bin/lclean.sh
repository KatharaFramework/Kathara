#!/bin/bash

python $NETKIT_HOME/python/check.py "$PWD/"

export RC=$?
if [ "$RC" = "0" ]; then

    M=_machines
    L=_links

    python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do ($NETKIT_HOME/wrapper/bin/netkit_dw rm -f `cat "$NETKIT_HOME/temp/$in$M"`; rm "$NETKIT_HOME/temp/$in$M"); done
    python $NETKIT_HOME/python/folder_hash.py "$PWD/" | while read in; do ($NETKIT_HOME/wrapper/bin/netkit_dw network rm `cat "$NETKIT_HOME/temp/$in$L"`; rm "$NETKIT_HOME/temp/$in$L"); done

else
    echo FAILED
fi
