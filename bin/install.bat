@echo off

ECHO win_bin=docker > %NETKIT_HOME%\..\config

SET SKIP_P4=1
SET NETKIT_APP=%1
SET SKIP_PIP=0
FOR %%p in (%*) DO (
    SET NETKIT_APP=%%p
    IF "%%p" == "--p4" ( 
        SET SKIP_P4=0
    )
    IF "%%p" == "--nopip" ( 
        SET SKIP_PIP=1
    )
)

echo "Pulling images"
docker pull kathara/netkit_base
docker pull alpine
IF "%SKIP_P4%" == "0" (
  docker pull kathara/p4
)

IF "%SKIP_PIP%" == "0" (
  echo "Checking ipaddress library"
  python -c "import ipaddress"
  IF "%ERRORLEVEL%" == "1" (
  echo "Installing ipaddress using pip (to skip use --nopip)"
    pip install ipaddress
  )
)
