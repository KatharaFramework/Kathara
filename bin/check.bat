@echo off

ECHO Docker version is
docker --version
echo.

ECHO Trying to run Docker Hello World
docker run --rm hello-world
echo.

ECHO Python version is
python -V
echo.

ECHO NETKIT_HOME is
ECHO %NETKIT_HOME%
echo.

ECHO Kathara version is
%NETKIT_HOME%\kathara_version.bat
echo.

ECHO Config file contents are
type %NETKIT_HOME%\..\config
echo.

ECHO Netkit temp folder contains
dir %NETKIT_HOME%\temp\
echo.