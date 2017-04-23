@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\vstart.py "%cd%/" %*') do CALL %NETKIT_HOME%\lstart -d %%a

RMDIR %NETKIT_HOME%\temp\labs\netkit_nt_%1 /S /Q
