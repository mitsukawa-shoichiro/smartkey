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

# 登録モード中、検知したIDmをGUI(card_check.py)へ送り返すための宛先。
# GUI側はこのポートでUDP受信待ちをする(daemon -> GUIの一方向通知)。
REGISTER_NOTIFY_HOST = '127.0.0.1'
REGISTER_NOTIFY_PORT = 10001

state = "authenticating"

REGISTERING_TIMEOUT_S = 45

state_changed_at = time.time()


BASE_DIR = os.path.dirname(__file__) + "\\..\\..\\config"
config_path = os.path.join(BASE_DIR, "usb_settings.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

COUNT_READER = config["設置台数"]

# 登録モードでIDmを受け付けるのは「出口」リーダーのみ(GUI案内文と一致させる)。
# get_readers()が返す reader_serial は config["devices"]["出口"]["serial"] と同じ値になる。
EXIT_READER_SERIAL = config["devices"]["出口"]["serial"]


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
    """
    キューで受け取った値を実際に認証する関数に渡す関数
    非同期送信スレッド、ポーリングをブロックしない
    """
    while True:
        #ここでキューから受け取り
        idm, reader_serial = event_q.get()
        try:
            #ここで認証
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
    """
    GUI側からくる認証/登録切り替えを受け取る関数

    """
    try:
        #localhost指定
        HEARTBEAT_HOST = '127.0.0.1'
        #受信ポート番号
        CardCheck_PORT = 10000
        sock_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_check.bind((HEARTBEAT_HOST, CardCheck_PORT))
        while (1):
            #ここで受け取り
            data, addr = sock_check.recvfrom(100)
            message = data.decode('utf-8')
            logger.info(f"状態:{message},{addr}")
            #実際に変更
            changeState(message)

    except Exception as e:
        logger.error(f"card_checkがメッセージ受信失敗: {e}")


def send_message(message, host=HEARTBEAT_HOST, port=HEARTBEAT_PORT):
    """
    UDPで1回だけメッセージを送る汎用関数。
    宛先を省略すると、従来通りcard_checkへのハートビート送信になる。
    登録モードの通知(GUI宛て)など、別ポートへ送りたい場合はhost/portを指定する。
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode('utf-8'), (host, port))
        sock.close()
    except Exception as e:
        logger.error(f"メッセージ送信失敗: {e} (宛先: {host}:{port}, 内容: {message})")


def notify_registered_card(idm: str):
    """
    登録モード中に出口リーダーで検知したIDmを、GUI(card_check.py)へ通知する。
    通常の認証フロー(event_q/card_sys.receive_card)は一切経由しない。
    """
    send_message(idm, host=REGISTER_NOTIFY_HOST, port=REGISTER_NOTIFY_PORT)
    logger.info(f"登録モード: IDmをGUIへ通知しました: {idm}")


def reader_loop():
    try:
        pythoncom.CoInitialize()
        logger.info(f"設定台数: {COUNT_READER}")
        get_reader()
        while True:
            reader_list = get_readers()
            # 全てのカードリーダーをチェック
            for reader, reader_serial in reader_list:
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

                        if state == "registering":
                            # 登録モード中は通常の認証フローに流さず、
                            # 出口リーダーで読めたIDmだけGUIへ通知する。
                            if reader_serial == EXIT_READER_SERIAL:
                                notify_registered_card(idm)
                        else:
                            event_q.put((idm, reader_serial))

                        logger.info(f"カードリーダー {reader_serial} でカードを検出、IDm: {idm}")
                        conn.disconnect()
                        break  # カードを検出したら他のリーダーをチェックしない
                    else:
                        conn.disconnect()

                except NoCardException:
                    conn.disconnect()
                except Exception as e:
                    logger.error(f"カードリーダー {reader_serial} でエラー: {e}")
                    continue

            global now
            gap = time.time() - now
            now = time.time()

            if gap > HEARTBEAT_ERROR_GAP_S:
                logger.error("card_check.pyのポーリングが遅延しています" + str(gap) + "秒")

            # GUI側のAUTHENTICATING変更が何かしらで中断されたとき用
            if state == "registering" and state_changed_at > REGISTERING_TIMEOUT_S:
                logger.warning(
                    f"登録状態が{REGISTERING_TIMEOUT_S}を超えたため、"
                    f"authenticatingへ強制変更します。"
                )
                changeState("authenticating")


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