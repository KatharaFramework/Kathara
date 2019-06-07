@echo off

python %NETKIT_HOME%\python\check.py "%cd%/" %*
IF ERRORLEVEL 1 GOTO END

python %NETKIT_HOME%\python\kinfo.py "%cd%/" %*

:END