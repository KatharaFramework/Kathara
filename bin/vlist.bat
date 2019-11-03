@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\adapter.py') DO SET ADAPTER_BIN=%%a

%ADAPTER_BIN% stats --no-stream & %ADAPTER_BIN% network list