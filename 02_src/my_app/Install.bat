@echo off

pushd "%~dp0"

py -m pip install --upgrade pip

py -m pip install -r requirements.txt --user

py service/windowsservice.py --startup delayed install

pause