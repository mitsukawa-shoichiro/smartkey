# Windowsサービスのエントリーポイント
from ast import Import
import logging
import subprocess
import os
import time
import sys

# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service
# endregion

logger = logs.log_config_service.logger

def start_api_server():
    """APIサーバーを起動"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    api_server_path = os.path.join(server_dir, "api_server.py")


    logger.info("APIサーバーを起動中...")
    return subprocess.Popen([sys.executable, api_server_path])

def start_card_reader():
    """カードリーダーを起動"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
    logger.info("カードリーダーを起動中...")
    return subprocess.Popen([sys.executable, card_reader_path])

def main():
    logger.info("システムを起動中...")



    # APIサーバーを起動
    api_process = start_api_server()
    time.sleep(1)  # APIサーバーの起動を待つ

    # カードリーダーを起動
    card_process = start_card_reader()

    logger.info("APIサーバーが起動されました")

    logger.info("システムが正常に起動しました！")
    logger.info("APIサーバー: http://127.0.0.1:5000")
    logger.info("カードリーダー: 動作中")
    logger.info("終了するには Ctrl+C を押してください")


if __name__ == "__main__":
    main()