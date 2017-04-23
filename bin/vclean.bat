@echo off

IF [%1]==[] GOTO USAGE

CALL %NETKIT_HOME%\lclean -d %NETKIT_HOME%\temp/labs/netkit_nt_%*

GOTO END

:USAGE
ECHO Usage: %0 machine_name 

:END
