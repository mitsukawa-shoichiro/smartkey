import time
from enum import Enum
import logging
from my_app.db import repository as repo
from my_app.models import ENUMS
from my_app.models.entity.access_log import AccessLog
from my_app.service.utils.lock_control import request_unlock
from my_app.config.reader_config import (
    EXIT_SERIAL, ENTRY_SERIAL, norm_serial)
from my_app.service.daemon_bridge.protocol import MODE_REGISTERING, MODE_AUTHENTICATING


#logに書き込む用
logger = logging.getLogger(__name__)


class CardReaderState(Enum):
    REGISTERING = MODE_REGISTERING      # カード登録状態
    AUTHENTICATING = MODE_AUTHENTICATING  # カード認証状態

# グローバル状態管理
current_state = CardReaderState.AUTHENTICATING  # デフォルト状態

def set_state(state: str):
    """
    現在のカードリーダー状態を設定します。
    :param state: "registering" または "authenticating"
    :return: 現在の状態文字列
    """
    global current_state
    if state == MODE_REGISTERING:
        current_state = CardReaderState.REGISTERING
    elif state == MODE_AUTHENTICATING:
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


last_card_id = None
last_card_timestamp = 0


def resolve_event_type(reader_serial):
    """
    リーダーシリアルから入室/退室を判定する。
    :return: ENUMS.EventType
    """
    s = norm_serial(reader_serial)
    if s is not None and s == EXIT_SERIAL:
        return ENUMS.EventType.EXIT
    if s is not None and s == ENTRY_SERIAL:
        return ENUMS.EventType.ENTRY
    logger.error("不明なリーダーIDです: %r (出口=%r, 入口=%r)",
                reader_serial, EXIT_SERIAL, ENTRY_SERIAL)
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
        if card_id != last_card_id or (time.monotonic() - last_card_timestamp > 6):

            user_id = repo.find_user_id_by_card_id(card_id)

            event_type = resolve_event_type(reader_serial)

            if not request_unlock(user_id):
                return

            last_card_id = card_id
            last_card_timestamp = time.monotonic()

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
