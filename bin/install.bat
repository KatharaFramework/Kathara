@echo off

ECHO win_bin=docker > %NETKIT_HOME%\..\config

SET SKIP_P4=1
SET NETKIT_APP=%1
SET SKIP_PIP=0
SET K8S=0

FOR %%p in (%*) DO (
    SET NETKIT_APP=%%p
    IF "%%p" == "--p4" ( 
        SET SKIP_P4=0
    )
    IF "%%p" == "--nopip" ( 
        SET SKIP_PIP=1
    )
    IF "%%p" == "--k8s" (
        SET K8S=1
    )
)

echo "Pulling images"
docker pull kathara/netkit_base
docker pull alpine
IF "%SKIP_P4%" == "0" (
  docker pull kathara/p4
)

IF "%SKIP_PIP%" == "0" (
  echo Checking ipaddress library
  python -c "exec('import ipaddress\nprint(\"Library already installed\")\n')"
  python -c "import ipaddress"
  IF ERRORLEVEL 1 GOTO pip

  IF "%K8S%" == "1" (
    echo Checking Kubernetes library
    python -c "exec('import kubernetes\nprint(\"Library already installed\")\n')"
    python -c "import kubernetes"
    IF ERRORLEVEL 1 GOTO k8s
  )
)

GOTO :exit

:pip
echo Installing ipaddress using pip (to skip use --nopip)
pip install ipaddress

:k8s
echo Installing kubernetes using pip (to skip use --nopip)
pip install urllib3==1.23
pip install kubernetes

:exit
