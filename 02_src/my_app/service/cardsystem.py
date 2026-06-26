from service.utils.sesame_bluetooth import open_sesame_bt
from service.utils.sesame import open_sesame
from service.nfcutils.card_scan import scan_card
from service.db_manager import check_card, insert_card_access_log
import sys
import os
import time
from enum import Enum
import asyncio
import logging
logger = logging.getLogger(__name__)#log書き込む陽


import threading
from service.utils.sesame import open_sesame, lock_sesame

import json
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', 'config', 'backend', 'sesame_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    connect_config = config_list["method"]["sesame_connect"]


class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating"  # カード認証状態


BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.." + "/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
sys.path.append('DataBase')

AUTO_LOCK_SECONDS = 10      # 開錠から自動施錠までの時間
_auto_lock_timer = None     # 自動ロックの時間もっとけ

# グローバル状態管理
current_state = CardReaderState.AUTHENTICATING  # デフォルト状態


def set_state(state: str):
    """
    現在のカードリーダー状態を設定します。
    :param state: "registering" または "authenticating"
    :return: 現在の状態文字列
    """
    global current_state
    if state == "registering":
        current_state = CardReaderState.REGISTERING
    elif state == "authenticating":
        current_state = CardReaderState.AUTHENTICATING
    else:
        raise ValueError(
            "Invalid state: must be 'registering' or 'authenticating'")
    return current_state.value


def get_state() -> str:
    """
    現在のカードリーダー状態を取得します。
    :return: 現在の状態文字列
    """
    return current_state.value


def get_card() -> str:
    """
    カードIDを読み取ります。
    :return: カードID
    """
    card_id = scan_card()
    if card_id is None:
        return ""
    return card_id


last_card_id = None
last_card_timestamp = 0


def receive_card(card_number: str, card_leader_id: int):
    """
    現在の状態に基づいてカードIDを処理します。
    card_id: カードID card_leader_id:カードリーダー番号
    """
    global last_card_id, last_card_timestamp
    card_id = check_card(card_number)
    if current_state == CardReaderState.AUTHENTICATING:
        if card_id:
            if card_id != last_card_id or (time.time() - last_card_timestamp > 6):
                last_card_id = card_id
                last_card_timestamp = time.time()

                request_unlock()

                insert_card_access_log(card_id, card_leader_id)
                logger.info(f"カード認証成功: {card_id} (リーダーID: {card_leader_id})")



def schedule_auto_lock():
    global _auto_lock_timer

    # タイマー動いてたらとめる
    if _auto_lock_timer is not None and _auto_lock_timer.is_alive():
        _auto_lock_timer.cancel()

    # 指定時間後にしめる
    _auto_lock_timer = threading.Timer(AUTO_LOCK_SECONDS, request_lock)
    _auto_lock_timer.daemon = True
    _auto_lock_timer.start()

def request_unlock():
    success = False
    # 接続方式で開錠   開錠成功＝successとして開錠された時のみunlockを要求
    if connect_config == "wifi":
        success = unlock()
    elif connect_config == "bluetooth":
        success = unlock_bt()

    # 開錠 -> 自動施錠予約
    if success:
        schedule_auto_lock()

def request_lock():
    # wifiの時SESAME APIであける
    try:
        if connect_config == "wifi":
            lock()
        elif connect_config == "bluetooth":
            logger.warning("Bluetooth lock is not implemented") 
            #Bluetoothでは未実装
    except Exception as e:      
        #例外の詳細を変数eに格納
        logger.exception(f"Auto lock failed:{e}")



def unlock():
    # Wi-Fiで開錠する
    return open_sesame()

def lock():
    # Wi-Fiで施錠する
    lock_sesame()


def unlock_bt():
    """
    Bluetoothを使用して解錠操作を実行します。
    """
    asyncio.run(open_sesame_bt())
