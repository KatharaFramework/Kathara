@echo off
setlocal enableDelayedExpansion

echo "This command will wipe containers and cache associated with Kathara"

python %NETKIT_HOME%\python\kclean.py --all "%cd%/" %*