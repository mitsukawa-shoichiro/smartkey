@echo off

pushd "%~dp0"

py service/windowsservice.py remove

pause