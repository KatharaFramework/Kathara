@echo off

echo "This command will wipe containers and cache associated with Kathara"

for /F "tokens=*" %%i in ('docker ps -a') do (
	for /F "tokens=*" %%d in ('%NETKIT_HOME%\python\rm_node_name_from_ps.py %%i') do docker %%d
)

for /F "tokens=*" %%n in ('docker network list') do (
	for /F "tokens=*" %%e in ('%NETKIT_HOME%\python\rm_network_name_from_list.py %%n') do docker %%e
)

set folder=%NETKIT_HOME%\temp\
cd /d %folder%
for /F "delims=" %%p in ('dir /b') do (
	IF NOT "%%p"=="labs" (del "%%p" /s/q)
)