@echo off

CALL %NETKIT_HOME%\lclean -d %NETKIT_HOME%\temp/labs/netkit_nt_%*

RMDIR %NETKIT_HOME%\temp\labs\netkit_nt_%* /S /Q

IF ERRORLEVEL 1 ECHO "FAILED"
