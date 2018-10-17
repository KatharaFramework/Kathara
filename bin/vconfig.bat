@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\adapter.py') DO SET ADAPTER_BIN=%%a

SET NETKIT_LASTARG=""
FOR %%a in (%*) do SET NETKIT_LASTARG=%%a

FOR %%p in (%*) DO (
    IF "%%p"=="%NETKIT_LASTARG%" GOTO ENDLOOP
    SET NETKIT_APP=%%p
    IF /i NOT "%NETKIT_APP:~0,1%" == "-" (
        CALL %ADAPTER_BIN% network create netkit_nt_%%p
        CALL %NETKIT_HOME%/brctl_config netkit_nt_%%p
        CALL %ADAPTER_BIN% network connect netkit_nt_%%p netkit_nt_%NETKIT_LASTARG%
    )
)

:ENDLOOP
