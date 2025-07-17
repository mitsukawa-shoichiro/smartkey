# reader_daemon.py
import time, json, threading, queue, requests, hashlib
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from smartcard.util import toHexString
import time
import sys
import os
import logging
# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service
# endregion

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from service import card_sys


POLL = [0x00, 0xFF, 0xFF, 0x01, 0x00]    # FeliCaポーリング


event_q = queue.Queue()


def sender():
    """非同期送信スレッド、ポーリングをブロックしない"""
    while True:
        idm = event_q.get()
        try:
            card_sys.receive_card(idm)
            print("送信成功")
            
        except Exception as e:
            print("送信失敗:", e)

def reader_loop():
    # 全てのカードリーダーを取得
    reader_list = readers()
    print("利用可能なカードリーダー:", reader_list)
    
    while True:
        # 全てのカードリーダーをチェック
        for i, reader in enumerate(reader_list):
            try:
                # カードリーダーに接続
                conn = reader.createConnection()
                conn.connect()
                
                # カードを読み取り
                GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                response, sw1, sw2 = conn.transmit(GET_IDM_APDU)
                
                # 読み取り成功の場合
                if [sw1, sw2] == [0x90, 0x00]:
                    idm = ''.join(format(byte, '02X') for byte in response)
                    event_q.put(idm)
                    print(f"カードリーダー {i+1} でカードを検出、IDm:", idm)
                    conn.disconnect()
                    break  # カードを検出したら他のリーダーをチェックしない
                else:
                    conn.disconnect()
                    
            except NoCardException:

                conn.disconnect()
            except Exception as e:
                print(f"カードリーダー {i+1} でエラー:", e)
                continue
        
        time.sleep(0.5)  # CPU負荷軽減

if __name__ == "__main__":
    threading.Thread(target=sender, daemon=True).start()
    reader_loop()
