rem coding: utf-8
@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist log mkdir log

set "watchdogLog=log\service-watchdog.log"

call :log "watchdog started"
call :log "workdir=%cd%"
call :log "waiting 20 seconds before first start"

timeout /t 20 /nobreak >nul

:restart
call :log "starting asr-server.exe"

asr-server.exe 2>> "%watchdogLog%"
rem 只把 asr-server.exe 的错误输出 stderr 追加写入 log\service-watchdog.log，普通输出 stdout 不再写入这个日志。

set "exitCode=%errorlevel%"

call :log "asr-server.exe exited, errorlevel=%exitCode%"
call :log "waiting 20 seconds before restart"

timeout /t 20 /nobreak >nul

goto restart

:log
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'"`) do set "now=%%i"
echo [%now%] %~1 >> "%watchdogLog%"
exit /b 0
