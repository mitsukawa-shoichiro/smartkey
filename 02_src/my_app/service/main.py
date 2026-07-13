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
from pathlib import Path
from db import schema
# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
from logs.log_config_service import logger
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "reader_daemon.py")
# backsys_path = os.path.join(server_dir, "sendmail", "back_system.py")

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))

from backsys import back_system
from daemon import reader_daemon


def run_back():
    logger.info("back_system thread started")
    back_system.main()

def run_card():
    logger.info("reader_daemon thread started")
    reader_daemon.main()

def main():
    logger.info("Service is starting...")
    db_path = Path("db/database.db")
    if not db_path.exists():
        logger.info("Database file does not exist. Creating database...")
        schema.create_database()
        logger.info("Database created successfully.")
    else:
        logger.info("Database file exists.")

    run_back()
    run_card()

if __name__ == "__main__":
    main()