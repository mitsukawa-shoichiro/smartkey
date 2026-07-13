# Windowsサービスのエントリーポイント
import logging
import subprocess
import os
import time
import sys
import logging
import win32serviceutil
import win32service
import win32event
import servicemanager
# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import my_app.logs.log_config_service
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
# backsys_path = os.path.join(server_dir, "sendmail", "BackSystem.py")



sys.path.append(os.path.dirname(__file__))

from my_app.service.backsystem import BackSystem

if __name__ == "__main__":
    BackSystem()