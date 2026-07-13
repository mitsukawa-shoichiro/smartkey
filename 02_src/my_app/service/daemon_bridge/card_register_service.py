"""
カード登録フローの判断ロジックをまとめるモジュール。

daemon(reader_daemon.py)との通信(UDP送信)、IDm受信待ち、重複チェックといったロジックを担当。
GUI操作は一切行わない。
呼び出し側(views/card_register.py)が、戻り値を見て画面を組み立てる。
"""
import socket
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import db.repository as repo
from my_app.service.daemon_bridge import thread_state
from my_app.service.daemon_bridge import register_listener

logger = logging.getLogger(__name__)

DAEMON_HOST = '127.0.0.1'
DAEMON_PORT = 10000  # reader_daemon.pyのreceiver()が待ち受けているポート

# wait_for_new_card の戻り値ステータス
STATUS_SUCCESS = "success"      # 未登録の新しいカードを検知した
STATUS_DUPLICATE = "duplicate"  # 既に登録済みのカードだった
STATUS_TIMEOUT = "timeout"      # 30秒待っても検知できなかった
STATUS_CANCELLED = "cancelled"  # ユーザーがキャンセルした


@dataclass
class CardWaitResult:
    status: str                  # STATUS_* のいずれか
    idm: Optional[str] = None    # 検知できた場合のIDm(タイムアウト/キャンセル時はNone)


def send_daemon_state(message: str):
    """
    daemonへ状態(registering/authenticating)をUDPで通知する。
    送信ごとに新しいソケットを使う(daemon側のsend_messageと同じ流儀。
    ソケットを使い回さないことで、複数スレッドから呼ばれても安全)。
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode('utf-8'), (DAEMON_HOST, DAEMON_PORT))
        sock.close()
        logger.info(f"daemonへ状態を送信しました: {message}")
    except OSError:
        logger.exception(f"daemonへの状態送信に失敗しました: {message}")


def start_registration_session():
    """
    登録セッションを開始する。
    daemonを登録モードへ切り替え、GUI側の受信リスナーを起動する。
    """
    thread_state.stop_event.clear()
    register_listener.start_listener()
    send_daemon_state("registering")


def cancel_registration_session():
    """
    登録セッションをユーザーの意思でキャンセルする。
    wait_for_new_card のループを止め、daemonを認証モードへ戻す。
    """
    thread_state.stop_event.set()
    register_listener.stop_listener()
    send_daemon_state("authenticating")


async def wait_for_new_card(timeout_total_s: int = 30) -> CardWaitResult:
    """
    daemonからのIDm通知を最大timeout_total_s秒待ち、結果を返す。
    daemon側は検知時に必ずAPDU応答を確認済みなので、2回連続一致確認は不要。

    このループの間、thread_state.stop_event が立てられたら
    STATUS_CANCELLED として即座に抜ける(キャンセルボタン対応)。

    register_listener.wait_for_card_number は threading.Event.wait を使う
    「頑固なブロッキング」関数なので、asyncio.to_thread で別スレッドに逃がして
    呼び出す。そのままawait無しで直接呼ぶと、この関数のイベントループ全体が
    ブロックされ、他の非同期処理(画面描画やキャンセル操作)を止めてしまう。

    Returns:
        CardWaitResult: status と、検知できた場合はidmを含む
    """
    for _ in range(timeout_total_s):
        if thread_state.stop_event.is_set():
            return CardWaitResult(status=STATUS_CANCELLED)

        idm = await asyncio.to_thread(register_listener.wait_for_card_number, 1.0)
        if idm is None:
            continue

        # 未登録/登録済みに関わらず、以降の再スキャンは不要なので登録モードを抜ける
        register_listener.stop_listener()
        send_daemon_state("authenticating")

        if repo.check_card(idm):
            return CardWaitResult(status=STATUS_DUPLICATE, idm=idm)
        return CardWaitResult(status=STATUS_SUCCESS, idm=idm)

    # timeout_total_s秒経ってもカードが検知できなかった場合
    register_listener.stop_listener()
    send_daemon_state("authenticating")
    return CardWaitResult(status=STATUS_TIMEOUT)


def register_card(card_number: str, card_type, user_id: int):
    """
    カードを登録する(DB挿入)。バリデーションは呼び出し側(GUI)の責務。

    Args:
        card_number (str): 読み取ったIDm
        card_type (CardType): カード種別
        user_id (int): 所有者のユーザーID

    Returns:
        int: 挿入されたカードのID
    """
    card_id = repo.insert_card(card_number, card_type, user_id)
    register_listener.clear_card_number()#これ今登録受信箱に入ってる値を空にするので結構大事
    logger.info(f"カードを登録しました: card_number={card_number}, user_id={user_id}")
    return card_id