@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\vstart.py "%cd%/" %*') do %NETKIT_HOME%\lstart -d "%%a"

IF ERRORLEVEL 1 ECHO "FAILED"
