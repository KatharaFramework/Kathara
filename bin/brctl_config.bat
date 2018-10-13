@ECHO off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\adapter.py') DO SET ADAPTER_BIN=%%a

FOR /F "tokens=*" %%a in ('%ADAPTER_BIN% network ls -qf "name=%*"') DO ( 
    echo Applying brctl patch to link %%a
    %ADAPTER_BIN% run --net=host --ipc=host --uts=host --pid=host -it --security-opt=seccomp=unconfined --privileged --rm -v /:/host alpine /usr/sbin/chroot /host /bin/ash -c "brctl setageing br-%%a 0; echo 65528 > /sys/class/net/br-%%a/bridge/group_fwd_mask"
)