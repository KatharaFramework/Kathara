@echo off

python %NETKIT_HOME%\python\check.py "%cd%/" %*
IF ERRORLEVEL 1 GOTO END

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\vstart.py "%cd%/" %*') do %NETKIT_HOME%\lstart -d "%%a"

:END