"""
カード登録フローの判断ロジックをまとめるモジュール。

daemon(reader_daemon.py)との通信(UDP送信)、IDm受信待ち、重複チェックといったロジックを担当。
GUI操作は一切行わない。
呼び出し側(views/card_register.py)が、戻り値を見て画面を組み立てる。
"""
import socket
import asyncio
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import my_app.db.repository as repo
from my_app.service.daemon_bridge import thread_state, register_listener
from my_app.service.daemon_bridge.protocol import DAEMON_MODE_PORT, LOCALHOST, MODE_AUTHENTICATING, MODE_REGISTERING
"""
DAEMON_MODE_PORT : 登録状態変更受信ポート番号
LOCALHOST : ローカルホスト用IPアドレス
MODE_REGISTERING : 登録状態変更の合言葉
MODE_AUTHENTICATING : 認証状態変更の合言葉
"""

logger = logging.getLogger(__name__)


class RegisterStatus(str, Enum):
    """
    wait_for_new_card の結果。
    strを継承しているので、呼び出し側が文字列と比較しても従来どおり動く。
    """
    SUCCESS = "success"        # 未登録の新しいカードを検知した
    DUPLICATE = "duplicate"    # 既に登録済みのカードだった
    TIMEOUT = "timeout"        # 制限時間内に検知できなかった
    CANCELLED = "cancelled"    # ユーザーがキャンセルした
    UNAVAILABLE = "unavailable"  # 受信ポートを確保できず登録を開始できなかった


# 旧名の互換エイリアス(呼び出し側の置き換えが済んだら削除)
STATUS_SUCCESS = RegisterStatus.SUCCESS
STATUS_DUPLICATE = RegisterStatus.DUPLICATE
STATUS_TIMEOUT = RegisterStatus.TIMEOUT
STATUS_CANCELLED = RegisterStatus.CANCELLED


@dataclass
class CardWaitResult:
    status: RegisterStatus
    idm: Optional[str] = None    # 検知できた場合のIDm(それ以外はNone)


def send_daemon_mode(mode: str):
    """
    daemonへモード(registering/authenticating)をUDPで通知する。
    送信ごとに新しいソケットを使う(複数スレッドから呼ばれても安全)。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(mode.encode('utf-8'), (LOCALHOST, DAEMON_MODE_PORT))
        logger.info("daemonへモードを送信しました: %s", mode)
    except OSError:
        logger.exception("daemonへのモード送信に失敗しました: %s", mode)


def start_registration_session() -> bool:
    """
    登録セッションを開始する。
    GUI側の受信リスナーを起動し、成功した場合のみdaemonを登録モードへ切り替える。

    Returns:
        bool: 開始できた -> True / 受信ポートを確保できなかった -> False
    """
    thread_state.stop_event.clear()

    if not register_listener.start_listener():
        logger.error("受信リスナーを起動できないため登録セッションを開始しません")
        return False

    send_daemon_mode(MODE_REGISTERING)
    return True


def cancel_registration_session():
    """
    登録セッションをユーザーの意思でキャンセルする。
    wait_for_new_card のループを止め、daemonを認証モードへ戻す。
    """
    thread_state.stop_event.set()
    register_listener.stop_listener()
    send_daemon_mode(MODE_AUTHENTICATING)


async def wait_for_new_card(timeout_total_s: int = 30) -> CardWaitResult:
    """
    daemonからのIDm通知を最大timeout_total_s秒待ち、結果を返す。
    daemon側は検知時に必ずAPDU応答を確認済みなので、2回連続一致確認は不要。

    thread_state.stop_event が立てられたらCANCELLEDで即座に抜ける(キャンセルボタン対応)。
    どの経路で抜けても、finallyでリスナー停止とdaemonの認証モード復帰を行う。

    Returns:
        CardWaitResult: status と、検知できた場合はidm
    """
    deadline = time.monotonic() + timeout_total_s
    try:
        while time.monotonic() < deadline:
            if thread_state.stop_event.is_set():
                return CardWaitResult(status=RegisterStatus.CANCELLED)

            idm = await asyncio.to_thread(register_listener.receive_idm, 1.0)
            if idm is None:
                continue

            if repo.check_card(idm):
                return CardWaitResult(status=RegisterStatus.DUPLICATE, idm=idm)
            return CardWaitResult(status=RegisterStatus.SUCCESS, idm=idm)

        return CardWaitResult(status=RegisterStatus.TIMEOUT)
    finally:
        # joinで最大2秒待つ可能性があるため、イベントループを止めないよう別スレッドで実行
        await asyncio.to_thread(register_listener.stop_listener)
        send_daemon_mode(MODE_AUTHENTICATING)


def register_card(idm: str, card_type, user_id: int) -> int:
    """
    カードを登録する(DB挿入)。バリデーションは呼び出し側(GUI)の責務。

    Args:
        idm (str): 読み取ったIDm
        card_type (CardType): カード種別
        user_id (int): 所有者のユーザーID

    Returns:
        int: 挿入されたカードの行ID
    """
    card_row_id = repo.insert_card(idm, card_type, user_id)
    register_listener.clear_idm()  # 受信箱に残った値を消す(次の登録に影響するので大事)
    logger.info("カードを登録しました: idm=%s, user_id=%s", idm, user_id)
    return card_row_id