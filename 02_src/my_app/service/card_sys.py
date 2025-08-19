import sys
import os
import time
from enum import Enum

import json
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'backend', 'connection.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    connect_config = config_list[1]




from .db_manager import check_card, insert_card_id
from .nfcutils.card_scan import scan_card
from .utils.sesame import open_sesame
from .utils.sesami_bluetooth import open_sesame_bt

class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating"  # カード認証状態


BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.." + "/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
sys.path.append('DataBase')

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
                
                if(connect_config):
                    unlock()
                else:
                    unlock_bt()

                
                
                insert_card_id(card_id, card_leader_id)


def unlock():
    """
    解錠操作を実行します。
    """
    open_sesame()
    
def unlock_bt():
    """
    Bluetoothを使用して解錠操作を実行します。
    """
    open_sesame_bt()
 




