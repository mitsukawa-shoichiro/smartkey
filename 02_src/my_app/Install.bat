@echo off

pushd "%~dp0"

py -m pip install --upgrade pip

py -m pip install -r requirements.txt

py service/windowsservice.py --startup delayed install

pause