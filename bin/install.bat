@echo off

docker rmi -f netkit
docker build -t netkit %NETKIT_HOME%