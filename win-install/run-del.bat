@echo off

rem "arguments serviceName"
@echo service:%1

rem "Enter current directory"
cd /d %~dp0
rem "Stop service"
net stop %1
rem "Uninstall service"
instsrv %1 remove

