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
from service.utils.usb_card_readers import get_readers
import time
import sys
import os
import logging
import socket
import pythoncom
import sqlite3

now = time.time()
HEARTBEAT_ERROR_GAP_S = 10
HEARTBEAT_HOST = '127.0.0.1'
HEARTBEAT_PORT = 54321
heart_beat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

state = "authenticating"

BASE_DIR = os.path.dirname(__file__) + "\\..\\..\\config"
config_path = os.path.join(BASE_DIR, "usb_settings.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

COUNT_READER = config["設置台数"]


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

logger = logging.getLogger(__name__)  # logに書き込む用

def sender():
    """非同期送信スレッド、ポーリングをブロックしない"""
    while True:
        idm, reader_serial = event_q.get()
        try:
            card_sys.receive_card(idm, reader_serial)
            logger.info(f"送信成功（リーダー{reader_serial+1}）")

        except sqlite3.Error as e:
            logger.error(f"DBエラーにより送信失敗: {e}")

        except Exception as e:
            logger.error(f"不明なエラーにより送信失敗: {e}")


def get_reader():
    reader_list = get_readers()  # [(reader, serial), ...]
    state = True
    logger.info(f"カードリーダーの数: {len(reader_list)}")
    while True:
        if len(reader_list) >= COUNT_READER:
            logger.info("カードリーダーの数が設定台数と一致しましたのでカードの読み込みがスタートしました。")
            return reader_list

        if COUNT_READER > len(reader_list) and state:
            logger.error(
                f"カードリーダーの数が不足しているためカードの読み込みがスタートしていません: {len(reader_list)} / {COUNT_READER}")
            state = False
        msg = "DEAD"
        send_message(msg)
        time.sleep(1)


def receiver():
    try:
        HEARTBEAT_HOST = '127.0.0.1'
        CardCheck_PORT = 10000
        sock_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_check.bind((HEARTBEAT_HOST, CardCheck_PORT))
        while (1):
            data, addr = sock_check.recvfrom(100)
            message = data.decode('utf-8')
            logger.info(f"状態:{message},{addr}")

            changeState(message)

    except Exception as e:
        logger.error(f"card_checkがメッセージ受信失敗: {e}")


def send_message(message):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode('utf-8'), (HEARTBEAT_HOST, HEARTBEAT_PORT))
        sock.close()
    except Exception as e:
        logger.error(f"card_checkがメッセージ送信失敗: {e}")
        logger.info(f"メッセージ送信失敗: {e}")


def reader_loop():
    try:
        pythoncom.CoInitialize()
        logger.info(f"設定台数: {COUNT_READER}")
        get_reader()
        while True:
            reader_list = get_readers()
            # 全てのカードリーダーをチェック
            for reader, number in reader_list:
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
                            event_q.put((idm, number))
                        logger.info(f"カードリーダー {number} でカードを検出、IDm: {idm}")
                        conn.disconnect()
                        break  # カードを検出したら他のリーダーをチェックしない
                    else:
                        conn.disconnect()

                except NoCardException:
                    conn.disconnect()
                except Exception as e:
                    logger.error(f"カードリーダー {number} でエラー: {e}")
                    continue

            global now
            gap = time.time() - now
            now = time.time()

            if gap > HEARTBEAT_ERROR_GAP_S:
                logger.error("card_check.pyのポーリングが遅延しています" + str(gap) + "秒")

            if (len(reader_list) < COUNT_READER):
                msg = "DEAD"
                send_message(msg)
            else:
                msg = "ALIVE"
                send_message(msg)

            time.sleep(1)  # CPU負荷軽減
            # break
    except Exception as e:
        logger.error(f"カードリーダーループでエラーが発生しました: {e}")
        send_message("DEAD")
        time.sleep(1)  # CPU負荷軽減


# REGISTERING = "registering"      # カード登録状態
# AUTHENTICATING = "authenticating"  # カード認証状態


def changeState(newState):
    global state
    state = newState
    logger.info(f"状態が変更されました: {state}")


def main():
    threading.Thread(target=sender, daemon=True).start()
    threading.Thread(target=receiver, daemon=True).start()
    threading.Thread(target=reader_loop, daemon=True).start()


if __name__ == "__main__":
    now = time.time()
