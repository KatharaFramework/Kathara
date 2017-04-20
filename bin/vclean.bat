@echo off

CALL %NETKIT_HOME%\lclean -d %NETKIT_HOME%\temp/labs/%*

RMDIR %NETKIT_HOME%\temp\labs\%* /S /Q

IF ERRORLEVEL 1 ECHO "FAILED"
