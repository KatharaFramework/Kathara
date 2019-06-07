@echo off

echo "Running in Kubernetes mode. No terminals will open."

python %NETKIT_HOME%\python\check.py "%cd%/" -f %*
IF ERRORLEVEL 1 GOTO END

python %NETKIT_HOME%\python\print_metadata.py "%cd%/" %*

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\folder_hash.py "%cd%/" %*') do SET VAR1=%NETKIT_HOME%\temp\%%a_deploy

if not exist %VAR1% (
    FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\lstart.py --k8s "%cd%/" %*') do (
        %%a
    )
) else (
    echo "Lab already deployed. Exiting..."
    GOTO END
)

:END