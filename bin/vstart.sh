#!/bin/bash

python $NETKIT_HOME/python/check.py "$PWD/" $@

export RC=$?
if [ "$RC" = "0" ]; then

    $NETKIT_HOME/lstart -d `python %NETKIT_HOME%\python\vstart.py "$PWD/" $@`

else
    echo FAILED
fi
