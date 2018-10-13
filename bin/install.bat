@echo off

ECHO win_bin=docker > %NETKIT_HOME%\..\config

SET SKIP_P4=1
SET NETKIT_APP=%1
FOR %%p in (%*) DO (
    SET NETKIT_APP=%%p
    IF "%%p" == "--p4" ( 
        SET SKIP_P4=0
    )
)

docker pull kathara/netkit_base
docker pull alpine
IF "%SKIP_P4%" == "0" (
  docker pull kathara/p4
)
