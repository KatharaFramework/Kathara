@echo off

FOR /F "tokens=*" %%a in ('python %NETKIT_HOME%\python\adapter.py') DO SET ADAPTER_BIN=%%a

echo "This command will wipe containers and cache associated with Kathara"

for /F "tokens=*" %%i in ('%ADAPTER_BIN% ps -a') do (
	for /F "tokens=*" %%d in ('%NETKIT_HOME%\python\rm_node_name_from_ps.py %%i') do %ADAPTER_BIN% %%d
)

for /F "tokens=*" %%n in ('%ADAPTER_BIN% network list') do (
	for /F "tokens=*" %%e in ('%NETKIT_HOME%\python\rm_network_name_from_list.py %%n') do %ADAPTER_BIN% %%e
)

set folder=%NETKIT_HOME%\temp\
cd /d %folder%
for /F "delims=" %%p in ('dir /b') do (
	IF NOT "%%p"=="labs" (del "%%p" /s/q)
)