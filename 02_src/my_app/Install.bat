@echo off
pushd "%~dp0"

if not exist "C:\smartkey\.venv\" (
    echo 仮想環境を作成します...
    python -m venv C:\smartkey\.venv
)

C:\smartkey\.venv\Scripts\python.exe -m pip install -r requirements.txt
C:\smartkey\.venv\Scripts\python.exe service\windowsservice.py --startup delayed install
pause