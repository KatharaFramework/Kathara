@echo off

python %NETKIT_HOME%\python\check.py

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\lstart.py %cd%\') do %%a