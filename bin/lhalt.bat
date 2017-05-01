@echo off

python %NETKIT_HOME%\python\check.py "%cd%/" %*
IF ERRORLEVEL 1 GOTO END

SET NETKIT_LIST=0
SET NETKIT_ALL=1
FOR %%t in (%*) DO (
    IF "%%t" == "--list" SET NETKIT_LIST=1
    ELSE docker stop  netkit_nt_%%t & SET NETKIT_ALL=0
)

IF "%NETKIT_ALL%" == "1" (
    FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') DO SET VAR1=%NETKIT_HOME%\temp\%%a_machines
    FOR /f "delims=" %%a in (%VAR1%) DO docker stop %%a
)

IF "%NETKIT_LIST%" == "1" docker ps -a & docker newtwork list

:END