"""
登録モード中、reader_daemon.pyから送られてくるIDm通知を受信するモジュール

daemon(別プロセス)が出口リーダーで検知したIDmをUDPで送ってくるので、
それを専用ポートで待ち受けて、GUI側から参照できる場所に保持します。

いろいろあってこの形にしました。
"""
import socket
import threading
import logging

logger = logging.getLogger(__name__)

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 10001  # reader_daemon.pyのREGISTER_NOTIFY_PORTと一致させること

# 受信したIDmを保持する状態
_latest_card_number: str | None = None
_lock = threading.Lock()
_new_card_event = threading.Event()  # 新しいIDmが届いたことを通知する

_listener_thread: threading.Thread | None = None
_stop_flag = threading.Event()


def _listen_loop():
    """UDPでIDm通知を待ち受け続けるループ。別スレッドで動かす想定。"""
    global _latest_card_number

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    sock.settimeout(1.0)  # stop()できるように、定期的にブロックを抜けさせる

    logger.info(f"登録モード通知の受信待機を開始しました: {LISTEN_HOST}:{LISTEN_PORT}")

    while not _stop_flag.is_set():
        try:
            data, addr = sock.recvfrom(100)
        except socket.timeout:
            continue
        except OSError:
            logger.exception("登録モード通知の受信中にソケットエラーが発生しました")
            break

        idm = data.decode('utf-8')
        logger.info(f"登録モード: daemonからIDmを受信しました: {idm} (from {addr})")

        with _lock:
            _latest_card_number = idm
        _new_card_event.set()

    sock.close()
    logger.info("登録モード通知の受信待機を終了しました")


def start_listener():
    """
    受信スレッドを開始する。registering画面の表示開始時に呼ぶこと。
    既に起動中であれば何もしない(多重起動防止)。
    """
    global _listener_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        return

    _stop_flag.clear()
    clear_card_number()
    _listener_thread = threading.Thread(target=_listen_loop, daemon=True)
    _listener_thread.start()


def stop_listener():
    """受信スレッドを止める。registering画面を離れる時に呼ぶこと。"""
    _stop_flag.set()


def clear_card_number():
    """保持しているIDmと通知フラグをリセットする(次の登録に備える)"""
    global _latest_card_number
    with _lock:
        _latest_card_number = None
    _new_card_event.clear()


def get_card_number() -> str | None:
    """現在保持している最新のIDmを取得する(無ければNone)"""
    with _lock:
        return _latest_card_number


def wait_for_card_number(timeout: float = 1.0) -> str | None:
    """
    新しいIDmが届くまで(最大timeout秒)待ってから、現在の値を返す。
    delayed_transitionのポーリングループから使うことを想定。

    Args:
        timeout (float): 最大待機秒数

    Returns:
        str | None: IDm(届いていなければNone)
    """
    _new_card_event.wait(timeout=timeout)
    _new_card_event.clear()
    return get_card_number()