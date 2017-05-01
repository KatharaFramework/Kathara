@echo off

IF [%1]==[] GOTO USAGE

FOR %%a in (%*) do SET NETKIT_LASTARG=%%a

CALL %NETKIT_HOME%\lclean -d %NETKIT_HOME%\temp/labs/netkit_nt_%NETKIT_LASTARG%

GOTO END

:USAGE
ECHO Usage: %0 machine_name 

:END
