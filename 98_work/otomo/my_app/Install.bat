@echo off

pushd "%~dp0"

python -m pip install -r requirements.txt

python .\windowsservice.py --startup delayed install

pause