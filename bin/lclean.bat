@echo off

python %NETKIT_HOME%\python\check.py %cd%\
IF ERRORLEVEL 1 GOTO END

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py %cd%\') do SET VAR1=%NETKIT_HOME%\temp\%%a_machines
FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py %cd%\') do SET VAR2=%NETKIT_HOME%\temp\%%a_links

FOR /f "delims=" %%a in (%VAR1%) do docker rm -f %%a
FOR /f "delims=" %%a in (%VAR2%) do docker network rm %%a

DEL %VAR1%
DEL %VAR2%

:END