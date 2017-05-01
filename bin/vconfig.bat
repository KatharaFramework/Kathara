@echo off

SET NETKIT_LASTARG=""
FOR %%a in (%*) do SET NETKIT_LASTARG=%%a

FOR %%p in (%*) DO (
    IF "%%p"=="%NETKIT_LASTARG%" GOTO ENDLOOP
    SET NETKIT_APP=%%p
    IF /i NOT "%NETKIT_APP:~0,1%" == "-" (
        CALL docker network create netkit_nt_%%p
        CALL docker network connect netkit_nt_%%p netkit_nt_%NETKIT_LASTARG%
    )
)

:ENDLOOP