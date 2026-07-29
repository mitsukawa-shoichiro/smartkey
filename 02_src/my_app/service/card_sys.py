from .utils.sesame_bluetooth import open_sesame_bt
from .nfcutils.card_scan import scan_card
import sys
import os
import time
from enum import Enum
import asyncio
import logging
from my_app.service.utils.sesame import open_sesame, lock_sesame
import json
from my_app.db import repository as repo
from my_app.models import ENUMS
from my_app.models.entity.access_log import AccessLog
from my_app.service.utils.lock_control import request_unlock
from my_app.config.config_loader import load_frontend_config, load_backend_config, get_value



CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', 'config', 'backend', 'sesame_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    connect_config = config_list["method"]["sesame_connect"]

#logに書き込む用
logger = logging.getLogger(__name__)

class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating"  # カード認証状態


BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.." + "/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
sys.path.append('DataBase')

AUTO_LOCK_SECONDS = 10      # 開錠から自動施錠までの時間

# グローバル状態管理
current_state = CardReaderState.AUTHENTICATING  # デフォルト状態

_reader_cfg = load_frontend_config("usb_settings.json")
_serial_cfg = get_value(_reader_cfg, "serial", None,  int)

_sesame_cfg = load_frontend_config("sesame_config.json")
_method_cfg = get_value(_sesame_cfg, "method", {}, dict)
_connect_cfg = get_value(_method_cfg, "sesame_connect", "wifi", str)


#カードリーダー設定読み込み
def load_config():
    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    CONFIG_PATH = os.path.normpath(
        os.path.join(base_dir, "config", "usb_settings.json")
    )
    logger.info(f"USB設定ファイルのパス: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["devices"]

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

def resolve_event_type(reader_serial: int) -> int:
    """
    カードIDとリーダーシリアル番号に基づいてイベントタイプを解決します。
    :param reader_serial: リーダーシリアル番号
    :return: イベントタイプ（1: 入室, 0: 退室）
    """
    config = load_config()
    if _serial_cfg == reader_serial:
        return ENUMS.EventType.EXIT
    elif _serial_cfg == reader_serial:
        return ENUMS.EventType.ENTRY
    else:
        logger.error(f"不明なリーダーIDです: {reader_serial}")
        raise ValueError("不明なリーダーIDです")

def receive_card(card_number: str, reader_serial: int):
    """
    カードIDの認証判断、解錠リクエスト、入退室ログ書き込み処理をする関数です。
    解錠を失敗した場合はログに残さないようにしています。
    また、SESAME_APIを叩くときに入退室したユーザーがわかるよう、
    request_unlockにuser_idを渡しています

    args:
        card_number : カードIDM(製造ID)
        reader_serial : リーダーID(0:1)

    params:
        last_card_id : 最後に認証したカードID
        last_card_time_stamp : 最後に認証した時刻

    """
    global last_card_id, last_card_timestamp
    card_id = repo.check_card(card_number)
    if card_id:
        if card_id != last_card_id or (time.time() - last_card_timestamp > 6):
            last_card_id = card_id
            last_card_timestamp = time.time()

            user_id = repo.find_user_id_by_card_id(card_id)

            event_type = resolve_event_type(reader_serial)

            if not request_unlock(user_id):
                return

            log = AccessLog(
                id=None,
                timestamp=None,
                method="カード",
                event_type=event_type,
                user_id=user_id,
                card_id=card_id
            )
            try:
                repo.insert_access_log(log) #入退室ログに書き込み
            except Exception:
                logger.exception("解錠後のログ書き込みを失敗user_id=%s card_id=%s", user_id, card_id)

            logger.info(f"カード認証成功: {card_id} (リーダーID: {reader_serial})")

    else:
        logger.warning("未登録カード: %s (リーダー%s)", card_number, reader_serial)


def request_lock(user_id: int):
    """
    施錠方式を判別、ユーザーIDを橋渡しする関数

    Args:
        user_id (int): ユーザーID
    """
    # wifiの時SESAME APIであける
    try:
        if connect_config == "wifi":
            lock(user_id)
        elif connect_config == "bluetooth":
            logger.warning("Bluetooth lock is not implemented")
            #Bluetoothでは未実装
    except Exception as e:
        #例外の詳細を変数eに格納
        logger.exception(f"Auto lock failed:{e}")

def unlock(user_id):
    """wi-fiで解錠する"""
    return open_sesame(user_id)

def lock(user_id):
    """Wi-Fiで施錠する"""
    return lock_sesame(user_id)

def unlock_bt(user_id):
    """
    Bluetoothを使用して解錠操作を実行します。
    """
    return asyncio.run(open_sesame_bt(user_id))

