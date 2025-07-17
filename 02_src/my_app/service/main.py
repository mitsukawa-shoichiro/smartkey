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


def start_card_reader():
    """カードリーダーを起動"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
    print("カードリーダーを起動中...")
    return subprocess.Popen([sys.executable, card_reader_path])

def main():
    print("システムを起動中...")
    # カードリーダーを起動
    card_process = start_card_reader()

    print("カードリーダー: 動作中")
    print("終了するには Ctrl+C を押してください")
    
 
if __name__ == "__main__":
    main() 