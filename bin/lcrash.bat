@echo off

python %NETKIT_HOME%\python\check.py "%cd%/" %*
IF ERRORLEVEL 1 GOTO END

SET NETKIT_LIST=0
SET NETKIT_ALL=1
SET NETKIT_APP=%1
FOR %%p in (%*) DO (
    SET NETKIT_APP=%%p
    IF "%%p" == "--list" ( 
        SET NETKIT_LIST=1
    )
    IF /i NOT "%NETKIT_APP:~0,1%" == "-" (
        SET NETKIT_ALL=0
        docker kill %%p
    )
)

IF "%NETKIT_ALL%" == "1" (
    FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') DO SET VAR1=%NETKIT_HOME%\temp\%%a_machines
    FOR /f "delims=" %%a in (%VAR1%) DO docker kill %%a
)

IF "%NETKIT_LIST%" == "1" docker stats --no-stream & docker network list

:END