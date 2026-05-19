rem coding: gbk
@echo off
cd /d "%~dp0"

if "%~1"=="" (
    echo serviceName is empty
    echo usage: run-install.bat hsAsrFunasrLargeService asr-server.exe
    pause
    exit /b 1
)

if "%~2"=="" (
    echo programName is empty
    echo usage: run-install.bat hsAsrFunasrLargeService asr-server.exe
    pause
    exit /b 1
)

set "serviceName=%~1"
set "programName=%~2"
set "appDir=%~dp0"
set "regpath=HKLM\SYSTEM\CurrentControlSet\Services\%serviceName%\Parameters"
set "sourcePath=%~dp0srvany.exe"
set "cmdPath=C:\Windows\System32\cmd.exe"
set "watchDog=%~dp0start-asr-server.bat"

if not exist "%sourcePath%" (
    echo srvany.exe not found: %sourcePath%
    pause
    exit /b 1
)

if not exist "%appDir%%programName%" (
    echo program not found: %appDir%%programName%
    pause
    exit /b 1
)

if not exist "%watchDog%" (
    echo watchdog script not found: %watchDog%
    pause
    exit /b 1
)

net stop "%serviceName%" >nul 2>nul
instsrv "%serviceName%" remove >nul 2>nul

instsrv "%serviceName%" "%sourcePath%"
echo Service add completed.

reg add "%regpath%" /v AppDirectory /t REG_SZ /d "%appDir%" /f
reg add "%regpath%" /v Application /t REG_SZ /d "%cmdPath%" /f
reg add "%regpath%" /v AppParameters /t REG_SZ /d "/d /c ""%watchDog%""" /f

sc config "%serviceName%" start= delayed-auto
reg add "HKLM\SYSTEM\CurrentControlSet\Services\%serviceName%" /v DelayedAutostart /t REG_DWORD /d 1 /f

sc failure "%serviceName%" reset= 86400 actions= restart/20000/restart/30000/restart/60000
sc failureflag "%serviceName%" 1

echo Starting service...
net start "%serviceName%"

echo Service auto-start configured.
