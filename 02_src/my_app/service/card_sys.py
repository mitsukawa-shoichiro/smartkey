import sys
import os
import time
from enum import Enum

path=os.path.dirname(__file__)

sys.path.append(path)
import db_manager
from nfcutils.card_scan import scan_card
from utils.sesame import open_sesame

class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating" # カード認証状態

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
        raise ValueError("Invalid state: must be 'registering' or 'authenticating'")
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

def receive_card(card_id: str,card_leader_id: int):
    """
    現在の状態に基づいてカードIDを処理します。
    :param card_id: カードID
    """
    if current_state == CardReaderState.AUTHENTICATING:
        if db_manager.check_card(card_id):
            unlock()
    
    elif current_state == CardReaderState.REGISTERING:
        get_card()
        
def unlock():
    """
    解錠操作を実行します。
    """
    open_sesame()
    time.sleep(6)


