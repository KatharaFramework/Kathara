@echo off

python %NETKIT_HOME%\python\check.py

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py %cd%\') do SET VAR1=%NETKIT_HOME%\temp\%%a_machines

FOR /f "delims=" %%a in (%VAR1%) do docker stats %%a
