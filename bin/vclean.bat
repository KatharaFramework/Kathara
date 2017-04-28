@echo off

IF [%1]==[] GOTO USAGE

for %%a in (%*) do SET NETKIT_LASTARG=%%a

SET FORCE_RT=""
:loop
IF NOT "%1"=="" (
    IF "%1"=="--remove-tunnels" (
        SET FORCE_RT="-f"
        SHIFT
    )
    IF "%1"=="-T" (
        SET FORCE_RT="-f"
        SHIFT
    )
    IF "%1"=="--clean-all" (
        SET FORCE_RT="-f"
        SHIFT
    )
    SHIFT
    GOTO :loop
)

CALL %NETKIT_HOME%\lclean %FORCE_RT% -d %NETKIT_HOME%\temp/labs/netkit_nt_%NETKIT_LASTARG%

GOTO END

:USAGE
ECHO Usage: %0 machine_name 

:END
