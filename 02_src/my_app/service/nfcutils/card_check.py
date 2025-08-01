# reader_daemon.py
from service import card_sys
import logs.log_config_service
import time
import json
import threading
import queue
import requests
import hashlib
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from smartcard.util import toHexString
import time
import sys
import os
import logging
import socket

HEARTBEAT_HOST = '127.0.0.1'
HEARTBEAT_PORT = 54321
heartbeatsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

state = "authenticating"


# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
# endregion

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


POLL = [0x00, 0xFF, 0xFF, 0x01, 0x00]    # FeliCaポーリング


event_q = queue.Queue()


def sender():
    """非同期送信スレッド、ポーリングをブロックしない"""
    while True:
        idm, i = event_q.get()
        try:
            card_sys.receive_card(idm, i)
            print(f"送信成功（リーダー{i+1}）")

        except Exception as e:
            print("送信失敗:", e)


def reciever():
    HEARTBEAT_HOST = '127.0.0.1'
    CardCheck_PORT = 10000
    sock_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_check.bind((HEARTBEAT_HOST, CardCheck_PORT))
    while (1):
        data, addr = sock_check.recvfrom(100)
        message = data.decode('utf-8')
        logging.info(f"状態:{message},{addr}")

        changeState(message)


def reader_loop():
    while True:
        # 全てのカードリーダーを取得
        reader_list = readers()
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
                    if (state != "registering"):
                        event_q.put((idm, i))
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
        if (len(reader_list) <= 1):

            msg = "DEAD"
            heartbeatsocket.sendto(msg.encode(
                'utf-8'), (HEARTBEAT_HOST, HEARTBEAT_PORT))
        else:
            msg = "ALIVE"
            heartbeatsocket.sendto(msg.encode(
                'utf-8'), (HEARTBEAT_HOST, HEARTBEAT_PORT))
        time.sleep(1)  # CPU負荷軽減
        # break


def main():
    threading.Thread(target=sender, daemon=True).start()
    threading.Thread(target=reciever, daemon=True).start()
    threading.Thread(target=reader_loop, daemon=True).start()


if __name__ == "__main__":
    main()

# REGISTERING = "registering"      # カード登録状態
# AUTHENTICATING = "authenticating"  # カード認証状態


def changeState(newState):
    global state
    state = newState
    print("現在のstate"+state)
