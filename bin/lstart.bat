@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\adapter.py') DO SET ADAPTER_BIN=%%a

python %NETKIT_HOME%\python\check.py "%cd%/" -f %*
IF ERRORLEVEL 1 GOTO END

python %NETKIT_HOME%\python\print_metadata.py "%cd%/" %*

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') do SET VAR1=%NETKIT_HOME%\temp\%%a_machines

if not exist %VAR1% (
    FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\lstart.py "%cd%/" %*') do ( 
        %%a
    )
) else (FOR /f "delims=" %%b in (%VAR1%) do %ADAPTER_BIN% start %%b & FOR /F "tokens=*" %%c in ('python %NETKIT_HOME%\python\lstart.py "%cd%/" --execbash %*') do %%c)

:END