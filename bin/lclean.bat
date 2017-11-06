@echo off

python %NETKIT_HOME%\python\check.py "%cd%/" %*
IF ERRORLEVEL 1 GOTO END

SET NETKIT_ALL=1
SET NETKIT_APP=%1
SET NETKIT_APP_PREV=%0
FOR %%p in (%*) DO (
    SET NETKIT_APP=%%p
    IF "%%p" == "--list" ( 
        SET NETKIT_LIST=1
    )
    IF NOT "%NETKIT_APP:~0,1%" == "-" (
        IF NOT "%NETKIT_APP_PREV%" == "-d" (
            SET NETKIT_ALL=0 
            docker rm -f netkit_nt_%%p
        )
    )
    SET NETKIT_APP_PREV=%%p
)

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') DO SET VAR1=%NETKIT_HOME%\temp\%%a_machines
FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') DO SET VAR2=%NETKIT_HOME%\temp\%%a_links

IF "%NETKIT_ALL%" == "1" (
    ECHO "Containers will be deleted"
    IF exist %VAR1% (
        FOR /f "delims=" %%a in (%VAR1%) DO docker rm -f %%a
    )
)
IF exist %VAR2% (
    FOR /f "delims=" %%a in (%VAR2%) DO docker network rm %%a
)

IF "%NETKIT_ALL%" == "1" (
    IF exist %VAR1% (
        DEL %VAR1%
    )
    IF exist %VAR2% (
        DEL %VAR2%
    )
)

:END