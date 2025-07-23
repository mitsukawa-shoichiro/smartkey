# Windowsサービスのエントリーポイント
from ast import Import
import logging
import subprocess
import os
import time
import sys
import logging
# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service
# endregion

server_dir = os.path.dirname(os.path.abspath(__file__))

def start_card_reader():
    """カードリーダーを起動"""
    card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
    print("カードリーダーを起動中...")
    subprocess.Popen([sys.executable, card_reader_path])

def start_BackSystem():
    backsys_path=os.path.join(server_dir, "sendmail", "BackSystem.py")
    subprocess.Popen([sys.executable, backsys_path])



def main():
    print("システムを起動中...")
    start_card_reader()
    start_BackSystem()
    logging.info("システムが起動されました")

if __name__ == "__main__":
    main() 