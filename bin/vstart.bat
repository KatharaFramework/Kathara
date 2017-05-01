@echo off

FOR %%a in (%*) do SET NETKIT_LASTARG=%%a

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\vstart.py "%cd%/" %*') do CALL %NETKIT_HOME%\lstart -d %%a

RMDIR %NETKIT_HOME%\temp\labs\netkit_nt_%NETKIT_LASTARG% /S /Q
