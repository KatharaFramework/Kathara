@echo off

python %NETKIT_HOME%\python\check.py %cd%\
IF ERRORLEVEL 1 GOTO END

python %NETKIT_HOME%\python\print_metadata.py %cd%\

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py %cd%\') do SET VAR1=%NETKIT_HOME%\temp\%%a_machines

if not exist %VAR1% (
    FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\lstart.py %* %cd%\') do %%a
) else (FOR /f "delims=" %%b in (%VAR1%) do docker start %%b & FOR /F "tokens=*" %%c in ('python %NETKIT_HOME%\python\lstart.py --execbash %* %cd%\') do %%c)

:END