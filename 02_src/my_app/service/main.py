# Windowsサービスのエントリーポイント
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
import logs.log_config_service
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
# backsys_path = os.path.join(server_dir, "sendmail", "BackSystem.py")

logger = logs.log_config_service.logger

sys.path.append(os.path.dirname(__file__))

from backsys import BackSystem
from nfcutils import card_check


def run_back():
    logger.info("BackSystem thread started")
    BackSystem.main()

def run_card():
    logger.info("CardCheck thread started")
    card_check.main()

import threading
def main():
    logger.info("Service is starting...")
    run_back()
    run_card()

if __name__ == "__main__":
    main()