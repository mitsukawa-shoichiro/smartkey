# Windowsサービスのエントリーポイント
import subprocess
import os
import time
import sys

def start_api_server():
    """APIサーバーを起動"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    api_server_path = os.path.join(server_dir, "api_server.py")
    print("APIサーバーを起動中...")
    return subprocess.Popen([sys.executable, api_server_path])

def start_card_reader():
    """カードリーダーを起動"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
    print("カードリーダーを起動中...")
    return subprocess.Popen([sys.executable, card_reader_path])

def main():
    print("システムを起動中...")
    
    # APIサーバーを起動
    api_process = start_api_server()
    time.sleep(1)  # APIサーバーの起動を待つ
    
    # カードリーダーを起動
    card_process = start_card_reader()
    
    print("システムが正常に起動しました！")
    print("APIサーバー: http://127.0.0.1:5000")
    print("カードリーダー: 動作中")
    print("終了するには Ctrl+C を押してください")
    
 
if __name__ == "__main__":
    main() 