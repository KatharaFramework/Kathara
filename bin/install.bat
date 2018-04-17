@echo off

ECHO win_bin=docker > %NETKIT_HOME%\python\config

docker pull kathara/netkit_base
docker pull kathara/p4